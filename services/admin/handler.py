from fdk.context import InvokeContext
import sys
import os
import subprocess
from typing import Callable, Dict, Union, Type

__all__ = ["create_handler", "create_async_handler", "MissingFunctionError"]


class MissingFunctionError(Exception):
    pass


def _one_hot_spare():
    """This function will (in the background) cause the function service
    to spin up another hot spare ready to process another request.
    This ensures that, if a user makes a request while this
    thread is busy, then the cold-start time to spin up another
    thread has been mitigated.

    Args:
         None
     Returns:
         None

    """
    devnull = open(os.devnull, "w")
    subprocess.Popen(
        ["nohup", sys.executable, "one_hot_spare.py"],
        stdout=devnull,
        stderr=subprocess.STDOUT,
    )


async def create_return_error(error: Type[Exception]) -> Dict:
    """Returns an error from an async function call handler

    Args:
        error: Exception raised
    Returns:
        dict: Dictionary packed for return
    """
    from Acquire.Service import create_return_value, pack_return_value, pop_is_running_service

    # Remove this running service from the
    pop_is_running_service()
    # Create a sensible return value from the exception
    error_return: Dict[str, Union[str, Dict]] = create_return_value(payload=error)
    # Pack the return value into a format expected
    return pack_return_value(payload=error_return)


def _base_handler(data: Union[bytes, Dict] = None, routing_function: Callable = None) -> Dict:
    """Handles asynchronous function calls for the functions. This brings together the old create_async_handler
    and base_handler functions
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


def _route_function(function: Union[str, None], args: Dict, routing_function: Callable = None):
    """Internal function that correctly routes the named function
    to the actual code to run (passing in 'args' as arguments).
    If 'additional_function' is supplied then this will also
    pass the function through 'additional_function' to find a
    match

    Args:
     function: Function to call
     args: arguments to be passed to the function
     additional_function (function, optional): another function used to
     process the function and arguments

     Returns:
        function : selected function
    """
    from importlib import import_module

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
        data = {"function": function, "args": args}
        return routing_function(ctx=None, data=data)
    else:
        raise MissingFunctionError(f"Unable to match call to {function} to known functions")


def _handle(
    ctx: InvokeContext = None,
    function: str = None,
    additional_function: Callable = None,
    args: Dict = None,
):
    """This function routes calls to sub-functions, thereby allowing
       a single identity function to stay hot for longer. If you want
       to add additional functions then add them via the
       'additional_function' argument. This should accept 'function'
       and 'args', returning some output if the function is found,
       or 'None' if the function is not available

       Args:
        additional_function (function, optional): function to route
        args (dict): arguments to be routed with function\
        Returns:
            function: the routed function
       """
    raise NotImplementedError

    from Acquire.Service import start_profile, end_profile

    if args is None:
        args = {}

    pr = start_profile()

    # if function != "warm":
    #     one_hot_spare()

    result = _route_function(ctx=ctx, function=function, args=args, additional_function=additional_function)

    end_profile(pr, result)

    return result


# def _base_handler(additional_function=None, ctx=None, data=None):
#     """This function routes calls to sub-functions, thereby allowing
#     a single function to stay hot for longer. If you want
#     to add additional functions then add them via the
#     'additional_function' argument. This should accept 'function'
#     and 'args', returning some output if the function is found,
#     or 'None' if the function is not available

#     Args:
#      additional_function (function): function to be routed
#      ctx: Invocation context passed to function if it's being called
#      data: to be passed as arguments to other functions

#      Returns:
#          dict: JSON serialisable dict
#     """
#     # Make sure we set the flag to say that this code is running
#     # as part of a service
#     from Acquire.Service import (
#         push_is_running_service,
#         pop_is_running_service,
#         unpack_arguments,
#         get_service_private_key,
#         pack_return_value,
#         create_return_value,
#     )

#     push_is_running_service()

#     # So this function unpacks the encrypted arguments sent by call_function
#     # Then it calls the function, here _handle is the function that controls the
#     # routing to the functions within each service
#     #

#     result = None

#     try:
#         function, args, keys = unpack_arguments(args=data, key=get_service_private_key)
#     except Exception as e:
#         function = None
#         args = None
#         result = e
#         keys = None

#     if result is None:
#         try:
#             result = _handle(
#                 ctx=ctx,
#                 function=function,
#                 additional_function=additional_function,
#                 args=args,
#             )
#         except Exception as e:
#             result = e

#     # Create a return value
#     return_value_result = create_return_value(payload=result)

#     try:
#         packed_result = pack_return_value(payload=return_value_result, key=keys)
#     except Exception as e:
#         packed_result = pack_return_value(payload=create_return_value(payload=e))

#     pop_is_running_service()

#     return packed_result


def create_async_handler(routing_function: Callable = None) -> Callable:
    """Function that creates the async handler functions for all standard
    functions, plus the passed routing_function

    Args:
        routing_function: Function to route call to if not internal call
    Returns:
        function: an async instance of the _base_handler function
    """

    async def async_handler(data: Dict = None):
        return _base_handler(routing_function=routing_function, data=data)

    return async_handler


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
        return _base_handler(routing_function=routing_function, data=data)

    return handler
