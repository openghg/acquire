from fdk.context import InvokeContext
from fdk.response import Response
from io import BytesIO
from typing import Dict, Union


def route(ctx: InvokeContext, data: Union[Dict, BytesIO]) -> Response:
    """Route the call to a specific registry function

    Args:
        ctx: Invoke context. This is passed by Fn to the function
        data: Data passed to the function by the user
    Returns:
        Response: Fn FDK response object containing function call data
        and data returned from function call
    """
    from acquire_caller.acquire_call import acquire_call

    # Then this can handle the function for each service without having to pass
    # additional_functions
    # return async_handler(ctx=ctx, data=data, service_name=service_name)

    service_name = "registry"

    return acquire_call(ctx=ctx, data=data, service_name=service_name)


