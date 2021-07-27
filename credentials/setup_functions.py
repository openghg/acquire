import json
import platform
import re
import pprint
import secrets
import subprocess
from pathlib import Path
from collections import defaultdict

from Acquire.Crypto import PrivateKey
from Acquire.ObjectStore import bytes_to_string

if not platform.system().lower().startswith("linux"):
    raise ValueError("This script will only work on Linux")

with open("services.json", "r") as f:
    services = json.load(f)["services"]
    services.sort()

with open("tenancy.json", "r") as f:
    tenancy_data = json.load(f)

for_output = defaultdict(dict)

print(
    "This script will create the required credentials for the Acquire serverless functions\n"
)

services_folder = Path(__file__).resolve(strict=True).parent.parent.joinpath("services")

service_url = (
    str(
        input("Please enter the Acquire service url (default: acquire.openghg.org) ")
        or "acquire.openghg.org"
    )
    .strip()
    .lower()
)

for service in services:

    data = {}
    data["tenancy"] = tenancy_data["tenancy_OCID"]
    data["region"] = tenancy_data["region"]

    print(f"\nWe are now setting up the *** {service} *** service\n")
    # OCID for the user
    data["user"] = input("Enter the user OCID: ")

    # Create the key, let the user upload it, ask them to confirm the fingerprint of the key
    passphrase = secrets.token_urlsafe(nbytes=32)
    service_path = services_folder.joinpath(service)

    cmd = f"openssl genrsa -out {service}.pem -aes256 -passout pass:{passphrase} 4096"
    cmd = cmd.split()
    subprocess.check_call(cmd, cwd=service_path)

    cmd = f"openssl rsa -pubout -in {service}.pem -out {service}_public.pem -passin pass:{passphrase}"
    cmd = cmd.split()
    subprocess.check_call(cmd, cwd=service_path)

    print(f"\nGenerated key for {service}\n")
    for_output[service]["key_passphrase"] = passphrase

    public_key_path = service_path.joinpath(f"{service}_public.pem")
    public_key_content = public_key_path.read_text()

    print(public_key_content)

    input(
        f"\n\nCopy the above key into the API key section for the {service} user, then press Enter."
    )

    key_fingerprint = input("Confirm fingerprint given by OCI for the key: ").lower().strip()

    # Now we calculate the MD5 sum of the public key and read it in
    cmd = f"openssl rsa -pubin -in {service}_public.pem -outform DER | openssl md5 -c"
    res = subprocess.check_output(cmd, shell=True, cwd=service_path)
    match = re.search("([0-9a-f]{2}:){15}[0-9a-f]{2}", str(res))

    if not match:
        raise ValueError("Could not calculate fingerprint from key")

    read_fingerprint = match.group().lower().strip()

    if read_fingerprint != key_fingerprint:
        raise ValueError(
            f"Incorrect key fingerprint given. \nCalculated {read_fingerprint}\nPassed: {key_fingerprint}\n"
        )

    data["key_lines"] = public_key_content
    data["fingerprint"] = key_fingerprint
    data["pass_phrase"] = passphrase

    private_key_path = service_path.joinpath(f"{service}.pem")
    # Make sure that this is the correct password...
    privkey = PrivateKey.read(private_key_path, passphrase)

    # Now we generate the secret_key file for the service
    secret_key_token = secrets.token_urlsafe(nbytes=32)
    secret_key_path = service_path.joinpath("secret_key")
    secret_key_path.write_text(secret_key_token)
    print(f"secret_key written to {str(secret_key_path)}")
    for_output[service]["secret_key"] = secret_key_token

    secret_config = {}
    secret_config["LOGIN"] = data

    bucket_data = {}
    data["compartment"] = input("Enter the bucket OCID: ")
    data["bucket"] = input("Enter bucket name :")

    secret_config["BUCKET"] = bucket_data
    secret_config["PASSWORD"] = passphrase

    config_key = PrivateKey()
    config_data = bytes_to_string(
        config_key.encrypt(json.dumps(secret_config).encode("utf-8"))
    )
    secret_key = json.dumps(config_key.to_data(secret_key_token))

    # Create the app for this service
    app_cmd = f"fn create app {service}"
    app_cmd = app_cmd.split()
    return_val = subprocess.call(app_cmd, cwd=service_path)

    host_cmd = f"fn config app {service} ACQUIRE_HOST {service_url}"
    subprocess.check_call(host_cmd, cwd=service_path)

    config_cmd = f"fn config app {service} SECRET_CONFIG '{config_data}'"
    config_cmd = config_cmd.split()
    subprocess.check_call(config_cmd, cwd=service_path)

    secret_cmd = f"fn config app {service} SECRET_KEY '{secret_key}'"
    secret_cmd = secret_cmd.split()
    subprocess.check_call(secret_cmd, cwd=service_path)

    input("\n\nPress enter to continue to the next service.....")

pp = pprint.PrettyPrinter(indent=4)
pp.pprint("Service passphrases and secret_keys:")
pp.pprint(for_output)
