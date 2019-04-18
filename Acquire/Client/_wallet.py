
# use a variable so we can monkey-patch while testing
_input = input

__all__ = ["Wallet"]


def _flush_output():
    """Flush STDOUT"""
    try:
        import sys as _sys
        _sys.stdout.flush()
    except:
        pass


def _read_json(filename, key=None):
    """Return a json-decoded dictionary from the data written
       to 'filename'
    """
    import json as _json
    with open(filename, "rb") as FILE:
        if key is not None:
            s = key.decrypt(FILE.read())
        else:
            s = FILE.read().decode("utf-8")

        return _json.loads(s)


def _write_json(data, filename, key=None):
    """Write the passed json-encodable dictionary to 'filename'"""
    import json as _json
    s = _json.dumps(data)
    with open(filename, "wb") as FILE:
        if key is not None:
            FILE.write(key.encrypt(s))
        else:
            FILE.write(s.encode("utf-8"))


def _read_service(filename):
    """Read and return the service written to 'filename'"""
    from Acquire.Client import Service as _Service
    return _Service.from_data(_read_json(filename))


def _write_service(service, filename):
    """Write the passed service to 'filename'"""
    _write_json(service.to_data(), filename)


def _could_match(userinfo, username, password):
    if username is None:
        return True

    if "username" not in userinfo:
        return False

    if userinfo["username"] == username:
        if password is None:
            return True

        if "password" in userinfo:
            if userinfo["password"] == password:
                return True

    return False


class Wallet:
    """This class holds a wallet that can be used to simplify
       sending passwords and one-time-password (OTP) codes
       to an acquire identity service.

       This holds a wallet of passwords and (optionally)
       OTP secrets that are encrypted using a local keypair
       that is unlocked by a password supplied by the user locally.

       By default this will create the wallet in your home
       directory ($HOME/.acquire_wallet). If you want the wallet
       to be saved in a different directory, specify that
       as "wallet_dir".
    """
    def __init__(self, wallet_dir=None, wallet_password=None):
        self._wallet_key = None
        self._service_info = {}

        import os as _os

        if wallet_dir is None:
            home = _os.path.expanduser("~")
            wallet_dir = "%s/.acquire_wallet" % home
            raise PermissionError("NO HOME IN TESTING")

        if not _os.path.exists(wallet_dir):
            _os.makedirs(wallet_dir, mode=0o700, exist_ok=False)
        elif not _os.path.isdir(wallet_dir):
            raise TypeError("The wallet directory must be a directory!")

        self._wallet_dir = wallet_dir

        if wallet_password is not None:
            self._get_wallet_key(wallet_password=wallet_password)

    def _create_wallet_key(self, filename, wallet_password=None):
        """Create a new wallet key for the user"""

        if wallet_password is not None:
            password = wallet_password
        else:
            import getpass as _getpass
            password = _getpass.getpass(
                     prompt="Please enter a password to encrypt your wallet: ")

        from Acquire.Client import PrivateKey as _PrivateKey
        key = _PrivateKey()

        bytes = key.bytes(password)

        if wallet_password is not None:
            password2 = wallet_password
        else:
            import getpass as _getpass
            password2 = _getpass.getpass(
                            prompt="Please confirm the password: ")

        if password != password2:
            print("The passwords don't match. Please try again.")
            self._create_wallet_key(filename)
            return

        # the passwords match - write this to the file
        with open(filename, "wb") as FILE:
            FILE.write(bytes)

        return key

    def _get_wallet_key(self, wallet_password=None):
        """Return the private key used to encrypt everything in the wallet.
           This will ask for the users password
        """
        if self._wallet_key:
            return self._wallet_key

        wallet_dir = self._wallet_dir

        keyfile = "%s/wallet_key.pem" % wallet_dir

        import os as _os

        if not _os.path.exists(keyfile):
            self._wallet_key = self._create_wallet_key(
                                            filename=keyfile,
                                            wallet_password=wallet_password)
            return self._wallet_key

        # read the keyfile and decrypt
        with open(keyfile, "rb") as FILE:
            bytes = FILE.read()

        wallet_key = None

        from Acquire.Client import PrivateKey as _PrivateKey

        if wallet_password is not None:
            wallet_key = _PrivateKey.read_bytes(bytes, wallet_password)

        # get the user password
        import getpass as _getpass
        while not wallet_key:
            password = _getpass.getpass(
                            prompt="Please enter your wallet password: ")

            try:
                wallet_key = _PrivateKey.read_bytes(bytes, password)
            except:
                print("Invalid password. Please try again.")

        self._wallet_key = wallet_key
        return wallet_key

    def _set_userinfo(self, userinfo, user_uid, identity_uid):
        """Save the userfile for the passed user_uid logging into the
           passed identity service with identity_uid
        """
        filename = self._get_userfile(user_uid=user_uid,
                                      identity_uid=identity_uid)
        key = self._get_wallet_key().public_key()
        _write_json(data=userinfo, filename=filename, key=key)

    def _get_userfile(self, user_uid, identity_uid):
        """Return the userfile for the passed user_uid logging into the
           passed identity service with identity_uid
        """
        assert(user_uid is not None)
        assert(identity_uid is not None)

        return "%s/user_%s_%s_encrypted" % (
            self._wallet_dir, user_uid, identity_uid)

    def _read_userinfo(self, user_uid, identity_uid):
        """Read all info for the passed user at the identity service
           reached at 'identity_url'"""
        key = self._get_wallet_key()
        filename = self._get_userfile(user_uid=user_uid,
                                      identity_uid=identity_uid)
        return _read_json(filename=filename, key=key)

    def _get_userinfo(self, username=None, password=None):
        """Function to find a user_info automatically, of if that fails,
           to ask the user
        """
        wallet_dir = self._wallet_dir

        import glob as _glob

        userfiles = _glob.glob("%s/user_*_encrypted" % wallet_dir)

        userinfos = []

        for userfile in userfiles:
            try:
                userinfo = self._read_userfile(userfile)
                if _could_match(userinfo, username, password):
                    userinfos.append((userinfo["username"], userinfo))
            except:
                pass

        userinfos.sort(key=lambda x: x[0])

        if len(userinfos) == 1:
            return userinfos[0][1]

        if len(userinfos) == 0:
            if username is None:
                username = _input("Please type your username: ")

            userinfo = {"username": username}

            if password is not None:
                userinfo["password"] = password

            return userinfo

        print("Please choose the account by typing in its number, "
              "or type a new username if you want a different account.")

        for (i, (username, userinfo)) in enumerate(userinfos):
            print("[%d] %s {%s}" % (i+1, username, userinfo["user_uid"]))

        while True:
            reply = _input(
                    "\nMake your selection (1 to %d) " %
                    (len(userinfos))
                )

            try:
                idx = int(reply) - 1

                if idx < 0 or idx >= len(userinfos):
                    print("Invalid account. Try again...")
                else:
                    return userinfos[idx][1]
            except:
                pass

    def _get_user_password(self, userinfo):
        """Get the user password for the passed user on the passed
           identity_url
        """
        if "password" in userinfo:
            return userinfo["password"]
        else:
            import getpass as _getpass
            password = _getpass.getpass(
                            prompt="Please enter the login password: ")
            userinfo["password"] = password
            return password

    def _get_otpcode(self, userinfo):
        """Get the OTP code"""
        if "otpsecret" in userinfo:
            from Acquire.Client import OTP as _OTP
            otp = _OTP(userinfo["otpsecret"])
            return otp.generate()
        else:
            import getpass as _getpass
            return _getpass.getpass(
                        prompt="Please enter the one-time-password code: ")

    def add_service(self, service):
        """Add a cached service info for the passed service. If it
           already exists, then this verifies that the added service
           is the same as the previously-seen service
        """
        from Acquire.ObjectStore import string_to_safestring \
            as _string_to_safestring

        service_file = "%s/service_%s" % (
            self._wallet_dir,
            _string_to_safestring(service.canonical_url()))

        existing_service = None

        try:
            existing_service = _read_service(service_file)
        except:
            pass

        if existing_service is not None:
            if service.validation_string() == \
               existing_service.validation_string():
                return service
            elif service.is_evolution_of(existing_service):
                # the service has evolved - this is ok
                _write_service(service, service_file)
                return service
            else:
                reply = _input(
                    "This is a service you have seen before, but "
                    "it has changed?\n\n"
                    "URL = %s (%s)\n"
                    "UID = %s (%s)\n"
                    "public_key fingerprint = %s (%s)\n"
                    "public_certificate fingerprint = %s (%s)\n\n"
                    "verification string = %s (%s)\n\n"
                    "\nDo you trust this updated service? y/n " %
                    (service.canonical_url(),
                     existing_service.canonical_url(),
                     service.uid(), existing_service.uid(),
                     service.public_key().fingerprint(),
                     existing_service.public_key().fingerprint(),
                     service.public_certificate().fingerprint(),
                     existing_service.public_certificate().fingerprint(),
                     service.validation_string(),
                     existing_service.validation_string())
                )

                if reply[0].lower() == 'y':
                    print("Now trusting %s" % str(service))
                else:
                    print("Not trusting this service!")
                    raise PermissionError(
                        "We do not trust the service '%s'" % str(service))

                # We trust the service, so save this for future reference
                _write_service(service, service_file)
                return service

        reply = _input(
                    "This is a new service that you have not seen before.\n\n"
                    "URL = %s\n"
                    "UID = %s\n"
                    "public_key fingerprint = %s\n"
                    "public_certificate fingerprint = %s\n\n"
                    "verification string = %s\n\n"
                    "\nDo you trust this service? y/n " %
                    (service.canonical_url(),
                     service.uid(),
                     service.public_key().fingerprint(),
                     service.public_certificate().fingerprint(),
                     service.validation_string())
                )

        if reply[0].lower() == 'y':
            print("Now trusting %s" % str(service))
        else:
            print("Not trusting this service!")
            raise PermissionError(
                "We do not trust the service '%s'" % str(service))

        # We trust the service, so save this for future reference
        _write_service(service, service_file)

        return service

    def get_services(self):
        """Return all of the trusted services known to this wallet"""
        import glob as _glob
        service_files = _glob.glob("%s/service_*" % self._wallet_dir)

        services = []

        for service_file in service_files:
            services.append(_read_service(service_file))

        return services

    def get_service(self, service_url):
        """Return the service at 'service_url'. This will return the
           cached service if it exists, or will add a new service if
           the user so wishes
        """
        from Acquire.ObjectStore import string_to_safestring \
            as _string_to_safestring

        service_file = "%s/service_%s" % (
            self._wallet_dir,
            _string_to_safestring(service_url))

        existing_service = None

        try:
            existing_service = _read_service(service_file)
        except:
            pass

        if existing_service is not None:
            # check if the keys need rotating - if they do, load up
            # the new keys and save them to the service file...
            if existing_service.should_refresh_keys():
                existing_service.refresh_keys()
                _write_service(existing_service, service_file)

            return existing_service
        else:
            from Acquire.Service import get_remote_service as \
                _get_remote_service

            service = _get_remote_service(service_url)
            return self.add_service(service)

    def remove_all_services(self):
        """Remove all trusted services from this Wallet"""
        import glob as _glob
        import os as _os
        service_files = _glob.glob("%s/service_*" % self._wallet_dir)

        for service_file in service_files:
            if _os.path.exists(service_file):
                _os.unlink(service_file)

        # clear cache to force a new lookup
        from ._service import _cache_service_lookup
        _cache_service_lookup.clear()

    def remove_service(self, service):
        """Remove the cached service info for the passed service"""
        if isinstance(service, str):
            service_url = service
        else:
            service_url = service.canonical_url()

        from Acquire.ObjectStore import string_to_safestring \
            as _string_to_safestring

        service_file = "%s/service_%s" % (
            self._wallet_dir,
            _string_to_safestring(service_url))

        import os as _os

        if _os.path.exists(service_file):
            _os.unlink(service_file)

        # clear cache to force a new lookup
        from ._service import _cache_service_lookup
        _cache_service_lookup.clear()

    def send_password(self, url, username=None, password=None,
                      otpcode=None, remember_password=True,
                      remember_device=None, dryrun=None):
        """Send a password and one-time code to the supplied login url"""
        if not remember_password:
            remember_device = False

        # the login URL is of the form "server/code"
        words = url.split("/")
        identity_service = "/".join(words[0:-1])
        short_uid = words[-1].split("=")[-1]

        # now get the service
        service = self.get_service(identity_service)

        if not service.can_identify_users():
            from Acquire.Client import LoginError
            raise LoginError(
                "Service '%s' is unable to identify users! "
                "You cannot log into something that is not "
                "a valid identity service!" % (service))

        userinfo = self._get_userinfo(username=username,
                                      password=password)

        if "user_uid" in userinfo:
            user_uid = userinfo["user_uid"]
        else:
            user_uid = None

        print("Logging in using username '%s'" % username)

        try:
            device_uid = userinfo["device_uid"]
        except:
            device_uid = None

        if password is None:
            password = self._get_user_password(userinfo=userinfo)

        if otpcode is None:
            otpcode = self._get_otpcode(userinfo=userinfo)

        print("\nLogging in to '%s', session '%s'..." % (
              service.canonical_url(), short_uid), end="")

        _flush_output()

        if dryrun:
            print("Calling %s with username=%s, password=%s, otpcode=%s, "
                  "remember_device=%s, device_uid=%s, short_uid=%s" %
                  (service.canonical_url(), username, password, otpcode,
                   remember_device, device_uid, short_uid))
            return

        try:
            from Acquire.Client import Credentials as _Credentials

            creds = _Credentials(username=username, password=password,
                                 otpcode=otpcode, short_uid=short_uid,
                                 device_uid=device_uid)

            args = {"credentials": creds.to_data(identity_uid=service.uid()),
                    "user_uid": user_uid,
                    "remember_device": remember_device,
                    "short_uid": short_uid}

            response = service.call_function(function="login", args=args)
            print("SUCCEEDED!")
            _flush_output()
        except Exception as e:
            print("FAILED!")
            _flush_output()
            from Acquire.Client import LoginError
            raise LoginError("Failed to log in. %s" % e.args)

        if not remember_password:
            return

        try:
            returned_user_uid = response["user_uid"]

            if returned_user_uid != user_uid:
                # change of user?
                userinfo = {}
                user_uid = returned_user_uid
        except:
            # no user_uid, so nothing to save
            return

        if user_uid is None:
            # can't save anything
            return

        userinfo["username"] = username
        userinfo["password"] = password

        try:
            userinfo["device_uid"] = response["device_uid"]
        except:
            pass

        try:
            userinfo["otpsecret"] = response["otpsecret"]
        except:
            pass

        self._set_userinfo(userinfo=userinfo,
                           user_uid=user_uid, identity_uid=service.uid())
