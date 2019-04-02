
import datetime as _datetime
import json as _json
import os as _os

__all__ = ["PAR", "BucketReader", "BucketWriter", "ObjectReader",
           "ObjectWriter", "ComputeRunner"]


class PAR:
    """This class holds the result of a pre-authenticated request
       (a PAR - also called a pre-signed request). This holds a
       pre-authenticated URL to access either;

       (1) A individual object in an object store (read or write)
       (2) An entire bucket in the object store (write only)
       (3) A calculation to be performed on the compute service (start or stop)

       The PAR is created encrypted, so can only be used by the
       person or service that has access to the decryption key
    """
    def __init__(self, url=None, key=None, encrypt_key=None,
                 created_datetime=None,
                 expires_datetime=None,
                 is_readable=False,
                 is_writeable=False,
                 is_executable=False,
                 par_id=None, par_name=None,
                 storage_url=None,
                 driver=None):
        """Construct a PAR result by passing in the URL at which the
           object can be accessed, the UTC datetime when this expires,
           whether this is readable, writeable or executable, and
           the encryption key to use to encrypt the PAR.

           If this is an object store PAR, then optionally you can
           pass in the key for the object in the object store that
           this provides access to. If this is not supplied, then an
           entire bucket is accessed). If 'is_readable', then read-access
           has been granted, while if 'is_writeable' then write
           access has been granted.

           If 'is_executable' then this is a calculation PAR that triggers
           a calculation.

           Otherwise no access is possible.

           This also records the type of object store behind this PAR
           in the free-form string 'driver'. You can optionally supply
           the ID of the PAR by passing in 'par_id', the user-supplied name,
           of the PAR by passing in 'par_name', and the time it
           was created using 'created_datetime' (in the same format
           as 'expires_datetime' - should be a UTC datetime with UTC tzinfo)

           This also sets the URL of the storage service that created
           the PAR. This is needed so that the storage service can be
           told when the PAR is closed, so that it can be deleted.
        """
        if url is None:
            is_readable = True
            self._uid = None
        else:
            from Acquire.Crypto import PublicKey as _PublicKey
            from Acquire.Crypto import PrivateKey as _PrivateKey

            if isinstance(encrypt_key, _PrivateKey):
                encrypt_key = encrypt_key.public_key()

            if not isinstance(encrypt_key, _PublicKey):
                raise TypeError(
                    "You must supply a valid PublicKey to encrypt a PAR")

            url = encrypt_key.encrypt(url)

            from Acquire.ObjectStore import create_uuid as _create_uuid
            self._uid = _create_uuid()

        self._url = url
        self._key = key
        self._created_datetime = created_datetime
        self._expires_datetime = expires_datetime
        self._driver = driver
        self._par_id = par_id
        self._par_name = par_name
        self._storage_url = storage_url

        if is_readable:
            self._is_readable = True
        else:
            self._is_readable = False

        if is_writeable:
            self._is_writeable = True
        else:
            self._is_writeable = False

        if is_executable:
            self._is_executable = True
        else:
            self._is_executable = False

        if self._is_executable:
            self._is_readable = False
            self._is_writeable = False
        elif not (self._is_readable or self._is_writeable):
            from Acquire.Client import PARPermissionsError
            raise PARPermissionsError(
                "You cannot create a PAR that has no read or write "
                "or execute permissions!")
        else:
            self._is_executable = False

    def __str__(self):
        if self.seconds_remaining() < 1:
            return "PAR( expired )"
        elif self._is_executable:
            return "PAR( calculation, seconds_remaining=%s )" % \
                (self.seconds_remaining(buffer=0))
        if self._key is None:
            return "PAR( bucket=True, seconds_remaining=%s )" % \
                (self.seconds_remaining(buffer=0))
        else:
            return "PAR( key=%s, seconds_remaining=%s )" % \
                (self.key(), self.seconds_remaining(buffer=0))

    def _set_private_key(self, privkey):
        """Call this function to set the private key for this
           PAR. This is the private key that is used to
           decrypt the PAR, and is provided here if you want
           to use the PAR without having to always supply
           the key (by definition, you are the only person
           who has the key)
        """
        from Acquire.Crypto import PrivateKey as _PrivateKey

        if not isinstance(privkey, _PrivateKey):
            raise TypeError("The private key must be type PrivateKey")

        self._privkey = privkey

    def _get_privkey(self, decrypt_key=None):
        """Return the private key used to decrypt the PAR, passing in
           the user-supplied key if needed
        """
        try:
            if self._privkey is not None:
                return self._privkey
        except:
            pass

        if decrypt_key is None:
            raise PermissionError(
                "You must supply a private key to decrypt this PAR")

        from Acquire.Crypto import PrivateKey as _PrivateKey
        if not isinstance(decrypt_key, _PrivateKey):
            raise TypeError("The supplied private key must be type PrivateKey")

        return decrypt_key

    def is_null(self):
        """Return whether or not this is null"""
        return self._uid is None

    @staticmethod
    def checksum(data):
        """Return the checksum of the passed data. This is used either
           for validating data, and is also used to create a checksum
           of the URL so that the user can demonstrate that they can
           decrypt this PAR
        """
        from hashlib import md5 as _md5
        md5 = _md5()
        md5.update(data)
        return md5.hexdigest()

    def url(self, decrypt_key=None):
        """Return the URL at which the bucket/object can be accessed. This
           will raise a PARTimeoutError if the url has less than 30 seconds
           of validity left. Note that you must pass in the key used to
           decrypt the PAR"""
        if self.seconds_remaining(buffer=30) <= 0:
            from Acquire.Client import PARTimeoutError
            raise PARTimeoutError(
                "The URL behind this PAR has expired and is no longer valid")

        return self._get_privkey(decrypt_key).decrypt(self._url)

    def uid(self):
        """Return the UID of this PAR"""
        return self._uid

    def par_id(self):
        """Return the ID of the PAR, if this was supplied by the underlying
           driver. This could be useful for PAR management by the server
        """
        return self._par_id

    def par_name(self):
        """Return the user-supplied name of the PAR, if this was supplied
           by the user and supported by the underlying driver. This could
           be useful for PAR management by the server
        """
        return self._par_name

    def fingerprint(self):
        """Return a fingerprint for this PAR that can be used
           in authorisations
        """
        return self._uid

    def is_readable(self):
        """Return whether or not this PAR gives read access"""
        return self._is_readable

    def is_writeable(self):
        """Return whether or not this PAR gives write access"""
        return self._is_writeable

    def is_executable(self):
        """Return whether or not this is an executable job"""
        return self._is_executable

    def key(self):
        """Return the key for the object this accesses - this is None
           if the PAR grants access to the entire bucket"""
        return self._key

    def is_bucket(self):
        """Return whether or not this PAR is for an entire bucket"""
        return (self._key is None) and not (self.is_executable())

    def is_calculation(self):
        """Return whether or not this PAR is for a calculation"""
        return self._is_executable

    def is_object(self):
        """Return whether or not this PAR is for a single object"""
        return self._key is not None

    def driver(self):
        """Return the underlying object store driver used for this PAR"""
        return self._driver

    def seconds_remaining(self, buffer=30):
        """Return the number of seconds remaining before this PAR expires.
           This will return 0 if the PAR has already expired. To be safe,
           you should renew PARs if the number of seconds remaining is less
           than 60. This will subtract 'buffer' seconds from the actual
           validity to provide a buffer against race conditions (function
           says this is valid when it is not)
        """
        from Acquire.ObjectStore import get_datetime_now as _get_datetime_now
        now = _get_datetime_now()

        buffer = float(buffer)

        if buffer < 0:
            buffer = 0

        delta = (self._expires_datetime - now).total_seconds() - buffer

        if delta < 0:
            return 0
        else:
            return delta

    def read(self, decrypt_key=None):
        """Return an object that can be used to read data from this PAR"""
        if not self.is_readable():
            from Acquire.Client import PARPermissionsError
            raise PARPermissionsError(
                "You do not have permission to read from this PAR: %s" % self)

        if self.is_bucket():
            return BucketReader(self, self._get_privkey(decrypt_key))
        else:
            return ObjectReader(self, self._get_privkey(decrypt_key))

    def write(self, decrypt_key=None):
        """Return an object that can be used to write data to this PAR"""
        if not self.is_writeable():
            from Acquire.Client import PARPermissionsError
            raise PARPermissionsError(
                "You do not have permission to write to this PAR: %s" % self)

        if self.is_bucket():
            return BucketWriter(self, self._get_privkey(decrypt_key))
        else:
            return ObjectWriter(self, self._get_privkey(decrypt_key))

    def execute(self, decrypt_key=None):
        """Return an object that can be used to control execution of
           this PAR
        """
        if not self.is_executable():
            from Acquire.Client import PARPermissionsError
            raise PARPermissionsError(
                "You do not have permission to execute this PAR: %s" % self)

        return ComputeRunner(self, self._get_privkey(decrypt_key))

    def close(self, storage_url=None, storage_service=None, decrypt_key=None):
        """Close this PAR - this closes and deletes the PAR. You must
           pass in the decryption key so that you can validate that
           you have permission to read (and thus close) this PAR
        """
        if self.is_null():
            return

        if storage_url is None:
            if storage_service is not None:
                storage_url = storage_service.canonical_url()
            elif self._storage_url is not None:
                storage_url = self._storage_url

        if storage_url is None:
            # This is a PAR created on a local bucket - we can't close
            # this directly
            pass
        else:
            if storage_service is None:
                from Acquire.Client import Wallet as _Wallet
                storage_service = _Wallet.get_service(storage_url)

            url = self.url(decrypt_key=decrypt_key)

            args = {"par_uid": self._uid,
                    "url_checksum": PAR.checksum(url)}

            storage_service.call_function(func="close_par", args=args)

        # now that the PAR is closed, set it into a null state
        import copy as _copy
        par = PAR()
        self.__dict__ = _copy.copy(par.__dict__)

    def to_data(self, passphrase=None):
        """Return a json-serialisable dictionary that contains all data
           for this object
        """
        data = {}

        if self._url is None:
            return data

        from Acquire.ObjectStore import datetime_to_string \
            as _datetime_to_string
        from Acquire.ObjectStore import bytes_to_string \
            as _bytes_to_string

        data["url"] = _bytes_to_string(self._url)
        data["uid"] = self._uid
        data["key"] = self._key
        data["created_datetime"] = _datetime_to_string(self._created_datetime)
        data["expires_datetime"] = _datetime_to_string(self._expires_datetime)
        data["driver"] = self._driver
        data["par_id"] = self._par_id
        data["par_name"] = self._par_name
        data["is_readable"] = self._is_readable
        data["is_writeable"] = self._is_writeable
        data["is_executable"] = self._is_executable
        data["storage_url"] = self._storage_url

        try:
            privkey = self._privkey
        except:
            privkey = None

        if privkey is not None:
            if passphrase is not None:
                data["privkey"] = privkey.to_data(passphrase)

        return data

    @staticmethod
    def from_data(data, passphrase=None):
        """Return a PAR constructed from the passed json-deserliased
           dictionary
        """
        if data is None or len(data) == 0:
            return PAR()

        from Acquire.ObjectStore import string_to_datetime \
            as _string_to_datetime
        from Acquire.ObjectStore import string_to_bytes \
            as _string_to_bytes

        par = PAR()

        par._url = _string_to_bytes(data["url"])
        par._key = data["key"]
        par._uid = data["uid"]

        if par._key is not None:
            par._key = str(par._key)

        par._created_datetime = _string_to_datetime(data["created_datetime"])
        par._expires_datetime = _string_to_datetime(data["expires_datetime"])
        par._driver = data["driver"]
        par._par_id = data["par_id"]
        par._par_name = data["par_name"]
        par._is_readable = data["is_readable"]
        par._is_writeable = data["is_writeable"]
        par._is_executable = data["is_executable"]

        if "storage_url" in data:
            par._storage_url = data["storage_url"]

        if "privkey" in data:
            if passphrase is not None:
                from Acquire.Crypto import PrivateKey as _PrivateKey
                par._privkey = _PrivateKey.from_data(data["privkey"],
                                                     passphrase)

        return par


def _url_to_filepath(url):
    """Internal function used to strip the "file://" from the beginning
       of a file url
    """
    return url[7:]


def _read_local(url):
    """Internal function used to read data from the local testing object
       store
    """
    with open("%s._data" % _url_to_filepath(url), "rb") as FILE:
        return FILE.read()


def _read_remote(url):
    """Internal function used to read data from a remote URL"""
    status_code = None
    response = None

    try:
        from Acquire.Stubs import requests as _requests
        response = _requests.get(url)
        status_code = response.status_code
    except Exception as e:
        from Acquire.Client import PARReadError
        raise PARReadError(
            "Cannot read the remote PAR URL '%s' because of a possible "
            "nework issue: %s" % (url, str(e)))

    output = response.content

    if status_code != 200:
        from Acquire.Client import PARReadError
        raise PARReadError(
            "Failed to read data from the PAR URL. HTTP status code = %s, "
            "returned output: %s" % (status_code, output))

    return output


def _list_local(url):
    """Internal function to list all of the objects keys below 'url'"""
    local_dir = _url_to_filepath(url)

    keys = []

    for dirpath, _, filenames in _os.walk(local_dir):
        local_path = dirpath[len(local_dir):]
        has_local_path = (len(local_path) > 0)

        for filename in filenames:
            if filename.endswith("._data"):
                filename = filename[0:-6]

                if has_local_path:
                    keys.append("%s/%s" % (local_path, filename))
                else:
                    keys.append(filename)

    return keys


def _list_remote(url):
    """Internal function to list all of the objects keys below 'url'"""
    return []


def _write_local(url, data):
    """Internal function used to write data to a local file"""
    filename = "%s._data" % _url_to_filepath(url)

    try:
        with open(filename, 'wb') as FILE:
            FILE.write(data)
            FILE.flush()
    except:
        dir = "/".join(filename.split("/")[0:-1])
        _os.makedirs(dir, exist_ok=True)
        with open(filename, 'wb') as FILE:
            FILE.write(data)
            FILE.flush()


def _write_remote(url, data):
    """Internal function used to write data to the passed remote URL"""
    try:
        from Acquire.Stubs import requests as _requests
        response = _requests.put(url, data=data)
        status_code = response.status_code
    except Exception as e:
        from Acquire.Client import PARWriteError
        raise PARWriteError(
            "Cannot write data to the remote PAR URL '%s' because of a "
            "possible nework issue: %s" % (url, str(e)))

    if status_code != 200:
        from Acquire.Client import PARWriteError
        raise PARWriteError(
            "Cannot write data to the remote PAR URL '%s' because of a "
            "possible nework issue: %s" % (url, str(response.content)))


def _join_bucket_and_prefix(url, prefix):
    """Join together the passed url and prefix, returning the
       url directory and the remainig part which is the start
       of the file name
    """
    if prefix is None:
        return url

    parts = prefix.split("/")

    return ("%s/%s" % (url, "/".join(parts[0:-2])), parts[-1])


class BucketReader:
    """This class provides functions to enable reading data from a
       bucket via a PAR
    """
    def __init__(self, par=None, decrypt_key=None):
        if par:
            if not isinstance(par, PAR):
                raise TypeError(
                    "You can only create a BucketReader from a PAR")
            elif not par.is_bucket():
                raise ValueError(
                    "You can only create a BucketReader from a PAR that "
                    "represents an entire bucket: %s" % par)
            elif not par.is_readable():
                from Acquire.Client import PARPermissionsError
                raise PARPermissionsError(
                    "You cannot create a BucketReader from a PAR without "
                    "read permissions: %s" % par)

            self._par = par
            self._url = par.url(decrypt_key)
        else:
            self._par = None

    def get_object(self, key):
        """Return the binary data contained in the key 'key' in the
           passed bucket"""
        if self._par is None:
            from Acquire.Client import PARError
            raise PARError("You cannot read data from an empty PAR")

        while key.startswith("/"):
            key = key[1:]

        url = self._url

        if url.endswith("/"):
            url = "%s%s" % (url, key)
        else:
            url = "%s/%s" % (url, key)

        if url.startswith("file://"):
            return _read_local(url)
        else:
            return _read_remote(url)

    def get_object_as_file(self, key, filename):
        """Get the object contained in the key 'key' in the passed 'bucket'
           and writing this to the file called 'filename'"""
        objdata = self.get_object(key)

        with open(filename, "wb") as FILE:
            FILE.write(objdata)

    def get_string_object(self, key):
        """Return the string in 'bucket' associated with 'key'"""
        data = self.get_object(key)

        try:
            return data.decode("utf-8")
        except Exception as e:
            raise TypeError(
                "The object behind this PAR cannot be converted to a string. "
                "Error is: %s" % str(e))

    def get_object_from_json(self, key):
        """Return an object constructed from json stored at 'key' in
           the passed bucket. This raises an exception if there is no
           data or the PAR has expired
        """
        data = self.get_string_object(key)
        return _json.loads(data)

    def get_all_object_names(self, prefix=None):
        """Returns the names of all objects in the passed bucket"""
        (url, part) = _join_bucket_and_prefix(self._url, prefix)

        if url.startswith("file://"):
            objnames = _list_local(url)
        else:
            objnames = _list_remote(url)

        # scan the object names returned and discard the ones that don't
        # match the prefix
        matches = []

        if len(part) > 0:
            for objname in objnames:
                if objname.startswith(part):
                    objname = objname[len(part):]

                    while objname.startswith("/"):
                        objname = objname[1:]

                    matches.append(objname)
        else:
            matches = objnames

        return matches

    def get_all_objects(self, prefix=None):
        """Return all of the objects in the passed bucket"""
        names = self.get_all_object_names(prefix)

        objects = {}

        if prefix:
            for name in names:
                objects[name] = self.get_object(
                                    "%s/%s" % (prefix, name))
        else:
            for name in names:
                objects[name] = self.get_object(name)

        return objects

    def get_all_strings(self, prefix=None):
        """Return all of the strings in the passed bucket"""
        objects = self.get_all_objects(prefix)

        names = list(objects.keys())

        for name in names:
            try:
                s = objects[name].decode("utf-8")
                objects[name] = s
            except:
                del objects[name]

        return objects


class BucketWriter:
    """This class provides functions to enable writing data to a
       bucket via a PAR
    """
    def __init__(self, par=None, decrypt_key=None):
        if par:
            if not isinstance(par, PAR):
                raise TypeError(
                    "You can only create a BucketReader from a PAR")
            elif not par.is_bucket():
                raise ValueError(
                    "You can only create a BucketReader from a PAR that "
                    "represents an entire bucket: %s" % par)
            elif not par.is_writeable():
                from Acquire.Client import PARPermissionsError
                raise PARPermissionsError(
                    "You cannot create a BucketWriter from a PAR without "
                    "write permissions: %s" % par)

            self._par = par
            self._url = par.url(decrypt_key)
        else:
            self._par = None

    def set_object(self, key, data):
        """Set the value of 'key' in 'bucket' to binary 'data'"""
        if self._par is None:
            from Acquire.Client import PARError
            raise PARError("You cannot write data to an empty PAR")

        while key.startswith("/"):
            key = key[1:]

        url = self._url

        if url.endswith("/"):
            url = "%s%s" % (url, key)
        else:
            url = "%s/%s" % (url, key)

        if url.startswith("file://"):
            return _write_local(url, data)
        else:
            return _write_remote(url, data)

    def set_object_from_file(self, key, filename):
        """Set the value of 'key' in 'bucket' to equal the contents
           of the file located by 'filename'"""
        with open(filename, "rb") as FILE:
            data = FILE.read()
            self.set_object(key, data)

    def set_string_object(self, key, string_data):
        """Set the value of 'key' in 'bucket' to the string 'string_data'"""
        self.set_object(key, string_data.encode("utf-8"))

    def set_object_from_json(self, key, data):
        """Set the value of 'key' in 'bucket' to equal to contents
           of 'data', which has been encoded to json"""
        self.set_string_object(key, _json.dumps(data))


class ObjectReader:
    """This class provides functions for reading an object via a PAR"""
    def __init__(self, par=None, decrypt_key=None):
        if par:
            if not isinstance(par, PAR):
                raise TypeError(
                    "You can only create an ObjectReader from a PAR")
            elif par.is_bucket():
                raise ValueError(
                    "You can only create an ObjectReader from a PAR that "
                    "represents an object: %s" % par)
            elif not par.is_readable():
                from Acquire.Client import PARPermissionsError
                raise PARPermissionsError(
                    "You cannot create an ObjectReader from a PAR without "
                    "read permissions: %s" % par)

            self._par = par
            self._url = par.url(decrypt_key)
        else:
            self._par = None

    def get_object(self):
        """Return the binary data contained in this object"""
        if self._par is None:
            from Acquire.Client import PARError
            raise PARError("You cannot read data from an empty PAR")

        url = self._url

        if url.startswith("file://"):
            return _read_local(url)
        else:
            return _read_remote(url)

    def get_object_as_file(self, filename):
        """Get the object contained in this PAR and write this to
           the file called 'filename'"""
        objdata = self.get_object()

        with open(filename, "wb") as FILE:
            FILE.write(objdata)

    def get_string_object(self):
        """Return the object behind this PAR as a string (raises exception
           if it is not a string)'"""
        data = self.get_object()

        try:
            return data.decode("utf-8")
        except Exception as e:
            raise TypeError(
                "The object behind this PAR cannot be converted to a string. "
                "Error is: %s" % str(e))

    def get_object_from_json(self):
        """Return an object constructed from json stored at behind
           this PAR. This raises an exception if there is no data
           or the PAR has expired
        """
        data = self.get_string_object()
        return _json.loads(data)


class ObjectWriter(ObjectReader):
    """This is an extension of ObjectReader that also allows writing to
       the object via the PAR
    """
    def __init__(self, par=None, decrypt_key=None):
        if par:
            if not isinstance(par, PAR):
                raise TypeError(
                    "You can only create an ObjectReader from a PAR")
            elif par.is_bucket():
                raise ValueError(
                    "You can only create an ObjectReader from a PAR that "
                    "represents an object: %s" % par)
            elif not par.is_writeable():
                from Acquire.Client import PARPermissionsError
                raise PARPermissionsError(
                    "You cannot create an ObjectWriter from a PAR without "
                    "write permissions: %s" % par)

            self._par = par
            self._url = par.url(decrypt_key)
        else:
            self._par = None

    def set_object(self, data):
        """Set the value of the object behind this PAR to the binary 'data'"""
        if self._par is None:
            from Acquire.Client import PARError
            raise PARError("You cannot write data to an empty PAR")

        url = self._url

        if url.startswith("file://"):
            return _write_local(url, data)
        else:
            return _write_remote(url, data)

    def set_object_from_file(self, filename):
        """Set the value of the object behind this PAR to equal the contents
           of the file located by 'filename'"""
        with open(filename, "rb") as FILE:
            data = FILE.read()
            self.set_object(data)

    def set_string_object(self, string_data):
        """Set the value of the object behind this PAR to the
           string 'string_data'
        """
        self.set_object(string_data.encode("utf-8"))

    def set_object_from_json(self, data):
        """Set the value of the object behind this PAR to equal to contents
           of 'data', which has been encoded to json"""
        self.set_string_object(_json.dumps(data))


class ComputeRunner:
    """This class provides functions for executing a calculation
       pre-authorised by the passed PAR
    """
    def __init__(self, par=None, decrypt_key=None):
        if par:
            if not isinstance(par, PAR):
                raise TypeError(
                    "You can only create a ComputeRunner from a PAR")
            elif not par.is_executable():
                raise ValueError(
                    "You can only create a ComputeRunner from a PAR that "
                    "represents an executable calculation: %s" % par)

            self._par = par
            self._url = par.url(decrypt_key)
        else:
            self._par = None
