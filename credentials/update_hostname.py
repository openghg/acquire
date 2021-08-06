"""
This can be used to update the hostname used by the functions
"""
import json
from pathlib import Path
import subprocess

with open("services.json", "r") as f:
    services = json.load(f)["services"]
    services.sort()

service_url = input("Service url: ").strip().lower()

if service_url is None:
    raise ValueError("Enter a url such as acquire.openghg.org")

services_folder = Path(__file__).resolve(strict=True).parent.parent.joinpath("services")
for service in services:
    service_path = services_folder.joinpath(service)
    host_cmd = f"fn config app {service} ACQUIRE_HOST {service_url}"
    subprocess.check_call(host_cmd, cwd=service_path)
