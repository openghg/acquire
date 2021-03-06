from copy import copy as _copy
from Acquire.Service import Service as _Service
from ._errors import StorageServiceError

__all__ = ["StorageService"]


class StorageService(_Service):
    """This is a specialisation of Service for Storage Services"""

    def __init__(self, other=None):
        if isinstance(other, _Service):
            self.__dict__ = _copy(other.__dict__)

            if not self.is_storage_service():

                raise StorageServiceError(
                    "Cannot construct an StorageService from " "a service which is not an storage service!"
                )
        else:
            _Service.__init__(self)
            self._storage_compartment_id = None

    def _call_local_function(self, function, args):
        """Internal function called to short-cut local 'remote'
        function calls
        """
        from storage.route import storage_functions as _storage_functions
        from Acquire.Service import create_handler

        handler = create_handler(additional_function=_storage_functions)
        return handler(function=function, args=args)
