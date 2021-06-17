import asyncio
import fdk
import json
import sys
import os
import subprocess

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
    subprocess.Popen(["nohup", sys.executable, "one_hot_spare.py"], stdout=devnull, stderr=subprocess.STDOUT)


def _route_function(ctx, function, args, additional_function=None):
    """Internal function that correctly routes the named function
    to the actual code to run (passing in 'args' as arguments).
    If 'additional_function' is supplied then this will also
    pass the function through 'additional_function' to find a
    match

    Args:
     function (str): select the function to call
     args: arguments to be passed to the function
     additional_function (function, optional): another function used to
     process the function and arguments

     Returns:
         function : selected function
    """
    from importlib import import_module

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

    if additional_function is not None:
        data = {"function": function, "args": args}
        return additional_function(ctx=ctx, data=data)
    else:
        raise MissingFunctionError(f"Unable to match call to {function} to known functions")


def _handle(ctx=None, function=None, additional_function=None, args=None):
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

    from Acquire.Service import start_profile, end_profile

    if args is None:
        args = {}

    pr = start_profile()

    # if function != "warm":
    #     one_hot_spare()

    result = _route_function(ctx=ctx, function=function, args=args, additional_function=additional_function)

    end_profile(pr, result)

    return result


def _base_handler(additional_function=None, ctx=None, data=None, loop=None):
    """This function routes calls to sub-functions, thereby allowing
    a single function to stay hot for longer. If you want
    to add additional functions then add them via the
    'additional_function' argument. This should accept 'function'
    and 'args', returning some output if the function is found,
    or 'None' if the function is not available

    Args:
     additional_function (function): function to be routed
     ctx: currently unused
     data (str): to be passed as arguments to other functions
     loop: currently unused

     Returns:
         dict: JSON serialisable dict
    """

    # Make sure we set the flag to say that this code is running
    # as part of a service
    from Acquire.Service import (
        push_is_running_service,
        pop_is_running_service,
        unpack_arguments,
        get_service_private_key,
        pack_return_value,
        create_return_value,
    )

    push_is_running_service()

    result = None

    try:
        (function, args, keys) = unpack_arguments(data, get_service_private_key)
    except Exception as e:
        function = None
        args = None
        result = e
        keys = None

    if result is None:
        try:
            result = _handle(ctx=ctx, function=function, additional_function=additional_function, args=args)
        except Exception as e:
            result = e

    result = create_return_value(payload=result)

    try:
        result = pack_return_value(payload=result, key=keys)
    except Exception as e:
        result = pack_return_value(payload=create_return_value(e))

    pop_is_running_service()
    return result


def create_async_handler(additional_function=None):
    """Function that creates the async handler functions for all standard
    functions, plus the passed additional_function

    Args:
        additional_function (optional): other function for which to
        create an async handler

    Returns:
        function: an async instance of the _base_handler function

    """

    async def async_handler(ctx, data=None, loop=None):
        return _base_handler(additional_function=additional_function, ctx=ctx, data=data, loop=loop)

    return async_handler


def create_handler(additional_function=None):
    """Function that creates the handler functions for all standard functions,
    plus the passed additional_function

    Args:
         additional_function (optional): other function to pass into base_handler function
    Returns:
        function: Handler function
    """

    def handler(ctx=None, data=None, loop=None):
        """Handles routing to sub-functions

        Args:
            ctx: Invocation context
            data: Data to be passed to base handler
            loop: Unused
         Returns:
             function: A handler function
        """
        return _base_handler(additional_function=additional_function, ctx=ctx, data=data, loop=loop)

    return handler
