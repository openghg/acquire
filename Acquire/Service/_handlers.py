
from typing import Union, Callable, Dict

__all__ = ["handle_call", "create_handler"]


def handle_call(data: Union[bytes, Dict] = None, routing_function: Callable = None) -> Dict:
    """Handles asynchronous function calls for the functions. This brings together the old create_async_handler
    and base_handler functions

    Args:
        data: Data to be passed into function
        routing_function: If not local call, function call will be routed to this function
    Returns:
        dict: Dictionary of data
    """
    from Acquire.Service import (
        push_is_running_service,
        unpack_arguments,
        get_service_private_key,
        pop_is_running_service,
        pack_return_value,
        create_return_value,
    )

    push_is_running_service()

    result = None

    try:
        # Get the function name, arguments and keys for the function from the packed arguments
        function, args, keys = unpack_arguments(args=data, key=get_service_private_key)
    except Exception as e:
        function = None
        args = None
        result = e
        keys = None

    if result is None:
        try:
            # Route the function call and arguments either to our internal functions or the
            # the passed routing function once arguments have been unpacked and possibly decrypted
            result = _route_function(function=function, args=args, routing_function=routing_function)
        except Exception as e:
            result = e

    result = create_return_value(payload=result)

    try:
        result = pack_return_value(payload=result, key=keys)
    except Exception as e:
        err_return = create_return_value(payload=e)
        result = pack_return_value(payload=err_return)

    pop_is_running_service()

    return result


def _route_function(function: str, args: Dict, routing_function: Callable = None):
    """Internal function that correctly routes the named function
    to the actual code to run (passing in 'args' as arguments).
    If 'additional_function' is supplied then this will also
    pass the function through 'additional_function' to find a
    match

    Args:
        function: Function to call
        args: arguments to be passed to the function
        routing_function: external function to route call to
    Returns:
        function : selected function
    """
    from importlib import import_module
    from Acquire.Service import MissingFunctionError

    # Handle local Acquire functions
    if function is None:
        from admin.root import run as _root

        return _root(args)
    else:
        try:
            module = import_module(function)
            to_call = getattr(module, "run")
            return to_call(args)
        except ModuleNotFoundError:
            try:
                with_admin = f"admin.{function}"
                module = import_module(with_admin)
                to_call = getattr(module, "run")
                return to_call(args)
            except ModuleNotFoundError:
                pass

    # Handle external function call - this will route the function call to
    # another service / libraries' service
    if routing_function is not None:
        return routing_function(function_name=function, data=args)
    else:
        raise MissingFunctionError(f"Unable to match call to {function} to known functions")


def create_handler(routing_function: Callable = None) -> Callable:
    """Function that creates the handler functions for all standard functions,
    plus the passed routing_function

    Args:
         routing_function: Function to route call to if not internal call
    Returns:
        function: Handler function
    """

    def handler(data: Dict = None):
        """Handles routing to sub-functions

        Args:
            ctx: Invocation context
            data: Data to be passed to base handler
            loop: Unused
         Returns:
             function: A handler function
        """
        return handle_call(data=data, routing_function=routing_function)

    return handler
