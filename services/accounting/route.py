from fdk.context import InvokeContext
from fdk.response import Response
from io import BytesIO
from typing import Dict, Union


def route(ctx: InvokeContext, data: Dict):
    """Route the call to a specific registry function

    Args:
        ctx: Invoke context. This is passed by Fn to the function
        data: Data passed to the function by the user
    Returns:
        Response: Fn FDK response object containing function call data
        and data returned from function call
    """
    from acquire_caller.acquire_call import acquire_call

    service_name = "accounting"

    return acquire_call(data=data, service_name=service_name)


async def handle_invocation(ctx: InvokeContext, data: BytesIO) -> Response:
    """The endpoint for the function. This handles the POST request and passes it through
    to the handler

    Args:
        ctx: Invoke context. This is passed by Fn to the function
        data: Data passed to the function by the user
    Returns:
        Response: Fn FDK response object containing function call data
        and data returned from function call
    """
    from admin.handler import handle_call
    import traceback

    try:
        data = data.getvalue()
    except Exception:
        error_str = str(traceback.format_tb())
        return Response(ctx=ctx, response_data=error_str)

    returned_data = handle_call(data=data, routing_function=route)
    headers = {"Content-Type": "application/octet-stream"}

    return Response(ctx=ctx, response_data=returned_data, headers=headers)