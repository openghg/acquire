import os
from unittest import mock
from Acquire.Service import get_service_host


@mock.patch.dict(os.environ, {"ACQUIRE_HOST": "acquire.example.org"})
def test_get_service_host():
    url = get_service_host()
    assert url == "acquire.example.org"

    identity_url = get_service_host(service="identity")

    assert identity_url == "acquire.example.org/t/identity"


@mock.patch.dict(os.environ, {"ACQUIRE_HOST": "https://acquire.example.org"})
def test_get_service_host_with_https():
    url = get_service_host()
    assert url == "acquire.example.org"

    identity_url = get_service_host(service="identity")

    assert identity_url == "acquire.example.org/t/identity"
