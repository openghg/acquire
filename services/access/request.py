from Acquire.Identity import Authorisation, AuthorisationError
from Acquire.Access import Request

from typing import Dict


def run(args: Dict) -> None:
    """This function is used to handle requests to access resources

    Args:
        args: Arguments for data authentication service
    Returns:
        dict: Dictionary containing the status of the authorisation and a status message
    """
    status = 0
    message = None

    request = None
    authorisation = None

    if "request" in args:
        request = Request.from_data(args["request"])

    if "authorisation" in args:
        authorisation = Authorisation.from_data(args["authorisation"])

    if request is None:
        status = 0
        message = "No request"

    if authorisation is None:
        raise AuthorisationError(f"You must provide a valid authorisation to make the request {str(request)}")

    authorisation.verify(request.signature())
