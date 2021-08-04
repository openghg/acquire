import traceback
from typing import Dict
from importlib import import_module


def acquire_call(function_name: str, data: Dict, service_name: str) -> Dict:
    """Template to used to call a specific service function. This function is
        only called from the route functions of each respective function.

    Args:
        data: Data passed to the function by the user
        service_name: Name of service
    Returns:
        dict: Dictionary of data
    """
    # We'll try and import the correct module and then use the "run" function within that module
    module_name = f"{service_name}.{str(function_name)}"
    module = import_module(module_name)
    fn_to_call = getattr(module, "run")

    try:
        response_data = fn_to_call(args=data)
        return response_data
    except Exception:
        tb = traceback.format_exc()
        return {"Error": str(tb)}
