
import uuid as _uuid
from copy import copy as _copy

from Acquire.Crypto import PrivateKey as _PrivateKey
from Acquire.Crypto import PublicKey as _PublicKey

from Acquire.Service import call_function as _call_function
from Acquire.Service import Service as _Service

from ._errors import AccountingServiceError

__all__ = ["AccountingService", "AccountingServiceError"]


class AccountingService(_Service):
    """This is a specialisation of Service for Accounting Services"""
    def __init__(self, other=None):
        if isinstance(other, _Service):
            self.__dict__ = _copy(other.__dict__)

            if not self.is_accounting_service():
                raise AccountingServiceError(
                    "Cannot construct an AccountingService from "
                    "a service which is not an accounting service!")
        else:
            _Service.__init__(self)

    def _call_local_function(self, function, args):
        """Internal function called to short-cut local 'remote'
           function calls
        """
        from accounting.route import accounting_functions \
            as _accounting_functions
        from admin.handler import create_handler as _create_handler
        handler = _create_handler(_accounting_functions)
        return handler(function, args)