import argparse
import json
import platform
import re
import pprint
import secrets
import subprocess
from shlex import quote
from pathlib import Path
from collections import defaultdict

from Acquire.Crypto import PrivateKey
from Acquire.ObjectStore import bytes_to_string

if not platform.system().lower().startswith("linux"):
    raise ValueError("This script will only work on Linux")

parser = argparse.ArgumentParser()
parser.add_argument("-ci", help="create mock credentials for testing services with CI pipeline", action="store_true")
args = parser.parse_args()

running_ci = args.ci


with open("services.json", "r") as f:
    services = json.load(f)["services"]
    services.sort()

if running_ci:
    tenancy_filename = "tenancy_example.json"
else:
    tenancy_filename = "tenancy.json"

with open(tenancy_filename, "r") as f:
    tenancy_data = json.load(f)

for_output = defaultdict(dict)

print("This script will create the required credentials for the Acquire serverless functions\n")

services_folder = Path(__file__).resolve(strict=True).parent.parent.joinpath("services")

if running_ci:
    service_url = "acquire.openghg.org"
else:
    service_url = (
        str(
            input("Please enter the Acquire service url (default: acquire.openghg.org) ") or "acquire.openghg.org"
        )
        .strip()
        .lower()
    )

    cloud_provider = (
        str(
            input("Please enter cloud provider (oci or gcp, default: oci) ") or "oci"
        )
        .strip()
        .lower()
    )


for service in services:
    data = {}
    data["tenancy"] = tenancy_data["tenancy_OCID"]
    data["region"] = tenancy_data["region"]

    print(f"\nWe are now setting up the *** {service} *** service\n")

    if running_ci:
        data["user"] = "test-ocid-user-123"
    else:
        # OCID for the user
        data["user"] = input("Enter the user OCID: ").strip()

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

    if not running_ci:
        print(public_key_content)

        input(f"\n\nCopy the above key into the API key section for the {service} user, then press Enter.")

        key_fingerprint = input("Confirm fingerprint given by OCI for the key: ").lower().strip()

    # Now we calculate the MD5 sum of the public key and read it in
    cmd = f"openssl rsa -pubin -in {service}_public.pem -outform DER | openssl md5 -c"
    res = subprocess.check_output(cmd, shell=True, cwd=service_path)
    match = re.search("([0-9a-f]{2}:){15}[0-9a-f]{2}", str(res))

    if not match:
        raise ValueError("Could not calculate fingerprint from key")

    read_fingerprint = match.group().lower().strip()

    if running_ci:
        saved_fingerprint = read_fingerprint
    else:
        if read_fingerprint != key_fingerprint:
            raise ValueError(
                f"Incorrect key fingerprint given. \nCalculated {read_fingerprint}\nPassed: {key_fingerprint}\n"
            )
        saved_fingerprint = key_fingerprint

    private_key_path = service_path.joinpath(f"{service}.pem")
    # Make sure that this is the correct password...
    privkey = PrivateKey.read(private_key_path, passphrase)
    private_key_content = private_key_path.read_text()

    data["key_lines"] = private_key_content
    data["fingerprint"] = saved_fingerprint
    data["pass_phrase"] = passphrase

    # Now we generate the secret_key file for the service
    secret_key_token = secrets.token_urlsafe(nbytes=32)
    secret_key_path = service_path.joinpath("secret_key")
    secret_key_path.write_text(secret_key_token)
    print(f"secret_key written to {str(secret_key_path)}")
    for_output[service]["secret_key"] = secret_key_token

    secret_config = {}
    secret_config["LOGIN"] = data

    bucket_data = {}

    if running_ci:
        bucket_data["compartment"] = "test-compartment-ocid-123"
        bucket_data["bucket"] = f"{service}_bucket"
    else:
        bucket_data["compartment"] = input("Enter the bucket OCID: ").strip()
        bucket_data["bucket"] = input("Enter bucket name :").strip()

    secret_config["BUCKET"] = bucket_data
    secret_config["PASSWORD"] = passphrase
    secret_config["CLOUD_BACKEND"] = cloud_provider

    config_key = PrivateKey()
    # This is the secret_config above encrypted using the key above
    config_data = bytes_to_string(config_key.encrypt(json.dumps(secret_config).encode("utf-8")))
    # Save the key used to encrypt the config data and encrypt that key's data with a passphrase
    secret_key = json.dumps(config_key.to_data(passphrase=secret_key_token))

    # Create the app for this service
    app_cmd = f"fn create app {service}"
    app_cmd = app_cmd.split()
    return_val = subprocess.call(app_cmd, cwd=service_path)

    host_cmd = f"fn config app {service} ACQUIRE_HOST '{service_url}'"
    subprocess.check_call(host_cmd, cwd=service_path, shell=True)

    config_cmd = f"fn config app {service} SECRET_CONFIG '{config_data}'"
    subprocess.check_call(config_cmd, cwd=service_path, shell=True)

    with open(secret_key_path) as f:
        password = f.readline()[0:-1]
    # Make sure we can read the key from the data we're giving the functions
    test_key = PrivateKey.from_data(data=json.loads(secret_key), passphrase=secret_key_token)

    secret_cmd = f"fn config app {service} SECRET_KEY '{secret_key}'"
    subprocess.check_call(secret_cmd, cwd=service_path, shell=True)

    if not running_ci:
        input("\n\nPress enter to continue to the next service.....")

if not running_ci:
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint("Service passphrases and secret_keys:")
    pp.pprint(for_output)
