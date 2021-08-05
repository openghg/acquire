import json as _json
from typing import Dict, Union, Type
from Acquire.Crypto import PublicKey

__all__ = [
    "call_function",
    "pack_arguments",
    "unpack_arguments",
    "create_return_value",
    "pack_return_value",
    "unpack_return_value",
    "exception_to_safe_exception",
    "exception_to_string",
]


def _get_signing_certificate(fingerprint=None, private_cert=None):
    """Return the signing certificate for this service"""
    if private_cert is not None:
        if private_cert.fingerprint() == fingerprint:
            return private_cert

    from ._service_account import (
        get_service_private_certificate as _get_service_private_certificate,
    )

    return _get_service_private_certificate(fingerprint=fingerprint)


def _get_key(key, fingerprint=None):
    """The user may pass the key in multiple ways. It could just be
    a key. Or it could be a function that gets the key on demand.
    Or it could be a dictionary that has the key stored under
    "encryption_public_key"
    """
    from Acquire.Crypto import PublicKey as _PublicKey
    from Acquire.Crypto import PrivateKey as _PrivateKey

    if key is None:
        return None
    elif isinstance(key, _PublicKey) or isinstance(key, _PrivateKey):
        key = key
    elif isinstance(key, dict):
        try:
            key = key["encryption_public_key"]
        except KeyError:
            key = None

        if key is not None:
            key = _PublicKey.read_bytes(key)
    else:
        key = key(fingerprint=fingerprint)

    if fingerprint is not None:
        if key is None:
            from Acquire.Crypto import KeyManipulationError

            raise KeyManipulationError("Cannot find the key with fingerprint %s!" % fingerprint)
        elif key.fingerprint() != fingerprint:
            from Acquire.Crypto import KeyManipulationError

            raise KeyManipulationError(
                "Cannot find a key with the required fingerprint (%s). "
                "The only key has fingerprint %s" % (fingerprint, key.fingerprint())
            )

    return key


def create_return_value(payload: Union[None, Type[Exception], Dict, str]) -> Dict:
    """Convenience function that creates a return value that can be
    passed back by a function. The 'payload' should either be
    a dictionary of return data, or it should be an exception.

    """
    try:
        if payload is None:
            return {"status": 0}

        elif isinstance(payload, Exception):
            err = {
                "class": str(payload.__class__.__name__),
                "module": str(payload.__class__.__module__),
                "error": str(payload),
            }

            if payload.__traceback__ is not None:
                import tblib as _tblib

                tb = _tblib.Traceback(payload.__traceback__)
                err["traceback"] = tb.to_dict()

            return {"status": -1, "exception": err}

        elif isinstance(payload, dict):
            return {"status": 0, "return": payload}
        else:
            return {"status": 0, "return": {"result": payload}}

    except Exception as e:
        return {"status": -3, "error": str(e)}


def pack_return_value(
    function=None,
    payload=None,
    key=None,
    response_key=None,
    public_cert=None,
    private_cert=None,
):
    """Pack the passed result into a json string, optionally
    encrypting the result with the passed key, and optionally
    supplying a public response key, with which the function
    being called should encrypt the response. If public_cert is
    provided then we will ask the service to sign their response.
    Note that you can only ask the service to sign their response
    if you provide a 'reponse_key' for them to encrypt it with too
    """
    from Acquire.ObjectStore import (
        get_datetime_now_to_string as _get_datetime_now_to_string,
    )
    import msgpack

    try:
        sign_result = key["sign_with_service_key"]
    except Exception:
        sign_result = False

    key = _get_key(key)
    response_key = _get_key(response_key)

    result = {}

    if function is None and "function" in payload:
        function = payload["function"]

    if response_key is not None:
        result["encryption_public_key"] = response_key.bytes()

        if public_cert:
            result["sign_with_service_key"] = public_cert.fingerprint()

    elif sign_result and key is None:
        from Acquire.Service import PackingError

        raise PackingError(
            "You cannot ask the service to sign the response without also providing a key to encrypt it with too"
        )

    result["payload"] = payload
    now = _get_datetime_now_to_string()
    result["synctime"] = now
    result["function"] = function

    if key is None:
        if sign_result:
            from Acquire.Service import PackingError

            raise PackingError("The service must encrypt the response before it can be signed.")
    else:
        response = {}
        # Use msgpack to pack the encrypted data
        result_bytes = msgpack.packb(result)
        encrypted_result = key.encrypt(result_bytes)

        if sign_result:
            # sign using the signing certificate for this service
            signature = _get_signing_certificate(fingerprint=sign_result, private_cert=private_cert).sign(
                encrypted_result
            )
            response["signature"] = signature

        response["data"] = encrypted_result
        response["encrypted"] = True
        response["fingerprint"] = key.fingerprint()
        response["synctime"] = now

        result = response

    packed = msgpack.packb(result)

    return packed


def pack_arguments(function=None, args=None, key=None, response_key: PublicKey = None, public_cert=None):
    """Pack the passed arguments, optionally encrypted using the passed key"""
    return pack_return_value(
        function=function,
        payload=args,
        key=key,
        response_key=response_key,
        public_cert=public_cert,
    )


def exception_to_safe_exception(e):
    """Convert the passed exception to a "safe" exception - this is one
    that can be copied because it does not hold references to any
    local data
    """
    if not issubclass(e.__class__, Exception):
        return TypeError(str(e))

    import tblib as _tblib

    tb = _tblib.Traceback(e.__traceback__)
    e.__traceback__ = tb.as_traceback()

    return e


def unpack_arguments(
    args: Union[str, bytes],
    key=None,
    public_cert=None,
    is_return_value: bool = False,
    function=None,
    service=None,
):
    """Call this to unpack the passed arguments that have been encoded
    as a json string, packed using pack_arguments.

    If is_return_value is True, then this will simply return
    the unpacked return value

    Otherwise, this will return a tuple containing

    (function, args, keys)

    where function is the name of the function to be called,
    args are the arguments to the function, and keys is a
    dictionary that may contain keys or additional instructions
    that will be used to package up the return value from
    calling the function.

    This function is also called as unpack_return_value, in which
    case is_return_value is set as True, and only the dictionary
    is returned. The 'function' on 'service'
    that was called (or to be called) can also be passed. These
    are used to help provide more context for error messages.


    Args:
        args: should be a JSON encoded UTF-8 string
        key
        public_cert
        is_return_value: Are we
        function
        service
    Returns:

    """
    import msgpack

    if not args:
        if is_return_value:
            return None
        else:
            return (None, None, None)

    try:
        data = msgpack.unpackb(args)
    except Exception as e:
        from Acquire.Service import UnpackingError

        raise UnpackingError("Cannot decode msgpack data from '%s' : %s" % (args, str(e)))

    # while not isinstance(data, dict):
    #     if not data:
    #         if is_return_value:
    #             return None
    #         else:
    #             return (None, None, None)

    #     try:
    #         data = _json.loads(data)
    #     except Exception as e:
    #         from Acquire.Service import UnpackingError

    #         raise UnpackingError("Cannot decode a json dictionary from '%s' : %s" % (data, str(e)))

    payload = data.get("payload")

    if is_return_value and payload is not None:
        # extra checks if this is a return value of a function rather
        # than the arguments
        if len(payload) == 1 and "error" in payload:
            from Acquire.Service import RemoteFunctionCallError

            raise RemoteFunctionCallError(
                "Calling %s on %s resulted in error: '%s'" % (function, service, payload["error"])
            )

        if "status" in payload:
            if payload["status"] != 0:
                if "exception" in payload:
                    _unpack_and_raise(function, service, payload["exception"])
                else:
                    from Acquire.Service import RemoteFunctionCallError

                    raise RemoteFunctionCallError(
                        "Calling %s on %s exited with status %d: %s"
                        % (function, service, payload["status"], payload)
                    )

    is_encrypted = data.get("encrypted", False)

    if public_cert is not None:
        if not is_encrypted:
            from Acquire.Service import UnpackingError

            raise UnpackingError(
                "Cannot unpack the result of %s on %s as it should be "
                "signed, but it isn't! (only encrypted results are signed) "
                "Response == %s" % (function, service, _json.dumps(data))
            )

        signature = data.get("signature")
        # try:
        #     # signature = _string_to_bytes(data["signature"])
        #     signature = data["signature"]
        # except KeyError:
        #     signature = None

        if signature is None:
            from Acquire.Service import UnpackingError

            raise UnpackingError(
                "We requested that the data was signed "
                "when calling %s on %s, but a signature was not provided!" % (function, service)
            )

    # Verify and decrypt the encrypted data
    if is_encrypted:
        encrypted_data = data["data"]
        fingerprint = data.get("fingerprint")

        if public_cert is not None:
            try:
                public_cert.verify(signature, encrypted_data)
            except Exception as e:
                raise UnpackingError(
                    "The signature of the returned data "
                    "from calling %s on %s "
                    "is incorrect and does not match what we "
                    "know! %s" % (function, service, str(e))
                )

        decrypted_data = _get_key(key=key, fingerprint=fingerprint).decrypt(encrypted_data)

        return unpack_arguments(
            args=decrypted_data,
            is_return_value=is_return_value,
            function=function,
            service=service,
        )

    if payload is None:
        from Acquire.Service import UnpackingError

        raise UnpackingError("We should have been able to extract the payload from " "%s" % data)

    # If this is a return value we just want to return the payload
    if is_return_value:
        try:
            return payload["return"]
        except KeyError:
            # no return value from this function
            return None
    else:
        function = data.get("function")

        return function, payload, data


def unpack_return_value(return_value: bytes, key=None, public_cert=None, function=None, service=None):
    """Call this to unpack the passed arguments that have been encoded
    by msgpack, packed using pack_arguments"""
    return unpack_arguments(
        args=return_value,
        key=key,
        public_cert=public_cert,
        is_return_value=True,
        function=function,
        service=service,
    )


class _UnicodeDecodeError(Exception):
    """Fake UnicodeDecodeError as the real one has a strange
    constructor syntax
    """

    pass


def _unpack_and_raise(function, service, exdata):
    """This function unpacks the exception whose data is in 'exdata',
    and raises it in the current thread. Additional information
    is added to the error message to include the remote function
    that was called (function) and the service on which it
    was called.

    The exdata should be a dictionary containing:

    class: class name of the exception
    module: module containing the exception
    traceback: json-serialised traceback (dumped using tbblib)
    error: error message of the exception
    """
    try:
        import importlib as _importlib
        import tblib as _tblib

        if exdata["class"] == "UnicodeDecodeError":
            exclass = _UnicodeDecodeError
        else:
            mod = _importlib.import_module(exdata["module"])
            exclass = getattr(mod, exdata["class"])

        ex = exclass("Error calling '%s' on '%s': %s" % (function, service, exdata["error"]))

        try:
            ex.__traceback__ = _tblib.Traceback.from_dict(exdata["traceback"]).as_traceback()
        except Exception:
            # cannot get the traceback...
            pass
    except Exception as e:
        from Acquire.Service import RemoteFunctionCallError
        from Acquire.Service import exception_to_string as _exception_to_string

        raise RemoteFunctionCallError(
            "An exception occurred while calling '%s' on '%s'\n\n"
            "CAUSE: %s\n\nEXDATA: %s" % (function, service, _exception_to_string(e), exdata)
        )

    raise ex


def exception_to_string(e):
    """This function returns a simple string that represents the exception,
    including the first line of the traceback.
    """
    import traceback as _traceback

    lines = _traceback.format_exception(e.__class__, e, e.__traceback__, limit=2)

    return "".join(lines)


def call_function(
    service_url,
    function: str = None,
    args: Dict = None,
    args_key=None,
    response_key=None,
    public_cert=None,
):
    """Call the remote function called 'function' at 'service_url' passing
    in named function arguments in 'kwargs'. If 'args_key' is supplied,
    then encrypt the arguments using 'args_key'. If 'response_key'
    is supplied, then tell the remote server to encrypt the response
    using the public version of 'response_key', so that we can
    decrypt it in the response. If 'public_cert' is supplied then
    we will ask the service to sign their response using their
    service signing certificate, and we will validate the
    signature using 'public_cert'
    """
    if args is None:
        args = {}

    from Acquire.Service import is_running_service as _is_running_service
    from Acquire.Stubs import requests as _requests

    service = None

    if _is_running_service():
        from Acquire.Service import get_this_service as _get_this_service

        try:
            service = _get_this_service(need_private_access=False)
        except Exception:
            pass

        if service is not None:
            if service.canonical_url() == service_url:
                result = service._call_local_function(function=function, args=args)
                return unpack_return_value(return_value=result)

    response_key = _get_key(response_key)

    # If we have a key encrypt the arguments and ask the function to encrypt
    # its response with the public key we give it
    if response_key:
        args_msgpack = pack_arguments(
            function=function,
            args=args,
            key=args_key,
            response_key=response_key.public_key(),
            public_cert=public_cert,
        )
    else:
        args_msgpack = pack_arguments(function=function, args=args, key=args_key)

    response = None

    try:
        response = _requests.post(
            url=service_url,
            data=args_msgpack,
            timeout=60.0,
        )
    except Exception as e:
        from Acquire.Service import RemoteFunctionCallError

        raise RemoteFunctionCallError(
            "Cannot call remote function '%s' at '%s' because of a possible "
            "network issue: requests exeption = '%s'" % (function, service_url, str(e))
        )

    args = None
    args_key = None

    # Check the call was a success
    if response.status_code != 200:
        from Acquire.Service import RemoteFunctionCallError

        raise RemoteFunctionCallError(
            "Cannot call remote function '%s' as '%s'. Invalid error code "
            "%d returned. Message:\n%s" % (function, service_url, response.status_code, str(response.content))
        )

    # Get the body of the data
    result = response.content

    try:
        # Get the fdk Response data
        result = response.body()
    except Exception:
        pass

    # Unpack the data here and pass in the private key for decryption
    unpacked_data = unpack_return_value(
        return_value=result,
        key=response_key,
        public_cert=public_cert,
        function=function,
        service=service_url,
    )

    return unpacked_data
