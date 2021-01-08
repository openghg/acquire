from fdk.context import InvokeContext
from fdk.response import Response
from typing import Dict, Union


def route(ctx: InvokeContext, data: Dict) -> Response:
    """ Route the call to a specific function

        Args:
            ctx: Invoke context. This is passed by Fn to the function
            data: Data passed to the function by the user
        Returns:
            Response: Fn FDK response object containing function call data
            and data returned from function call
    """
    # function = data["function"]
    # args = data["args"]

    headers = {"Content-type": "application/json"}
    
    response_data = {"this": "that"}

    return Response(ctx=ctx, response_data=response_data, headers=headers)

    # try:
    #     response_data = {"this": "that"}

    #     return Response(ctx=ctx, response_data=response_data, headers=headers)
    #     if function == "request":
    #         from access.request import run as _request

    #         response_data = _request(args)
    #     elif function == "run_calculation":
    #         from access.run_calculation import run as _run_calculation

    #         response_data = _run_calculation(args)
    #     else:
    #         response_data = {"Error": "Unknown function"}
        
    #     headers = {"Content-type": "application/json"}


    # except Exception:
    #     tb = traceback.format_exc()
    #     return Response(ctx=ctx, response_data={"error": str(tb)})





# def access_functions(function, args):
#     """This function routes the passed arguments to the function
#     selected by the function parameter.
#     """
#     if function == "request":
#         from access.request import run as _request

#         return _request(args)
#     elif function == "run_calculation":
#         from access.run_calculation import run as _run_calculation

#         return _run_calculation(args)
#     else:
#         from admin.handler import MissingFunctionError

#         raise MissingFunctionError()


# if __name__ == "__main__":
#     import fdk
#     from admin.handler import create_async_handler

#     fdk.handle(create_async_handler(access_functions))
