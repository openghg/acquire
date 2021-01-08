from fdk.context import InvokeContext
from fdk.response import Response
from io import BytesIO
import json
import traceback
from typing import Dict, Union
from importlib import import_module


def call_fn(ctx: InvokeContext, data: Union[Dict, BytesIO], service_name: str) -> Response:
    """ Template to used to call a specific service function. This function is
        only called from the route functions of each respective function.

    Args:
        ctx: Invoke context. This is passed by Fn to the function
        data: Data passed to the function by the user
    Returns:
        Response: Fn FDK response object containing function call data
        and data returned from function call
    """
    try:
        data = json.loads(data)
    except Exception:
        try:
            data = json.loads(data.getvalue())
        except Exception:
            tb = traceback.format_exc()
            return Response(ctx=ctx, response_data={"Error": str(tb)})

    submodule_name = data["function"]
    args = data["args"]

    module_name = ".".join((service_name, str(submodule_name)))
    module = import_module(module_name)
    fn_to_call = getattr(module, "run")

    try:
        response_data = fn_to_call(args=args)
        headers = {"Content-type": "application/json"}

        return Response(ctx=ctx, response_data=response_data, headers=headers)
    except Exception:
        tb = traceback.format_exc()
        error_data = {"Error": str(tb)}
        return Response(ctx=ctx, response_data=error_data)
