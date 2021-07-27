import os
from unittest import mock
from Acquire.Service import get_service_url


@mock.patch.dict(os.environ, {"ACQUIRE_HOST": "acquire.example.org"})
def test_get_service_url():
    url = get_service_url(https=False)
    assert url == "acquire.example.org"

    url = get_service_url(https=True)
    assert url == "https://acquire.example.org"

    identity_url = get_service_url(service="identity", https=False)

    assert identity_url == "acquire.example.org/t/identity"

    identity_url = get_service_url(service="identity", https=True)

    assert identity_url == "https://acquire.example.org/t/identity"


@mock.patch.dict(os.environ, {"ACQUIRE_HOST": "https://acquire.example.org"})
def test_get_service_url_with_https():
    url = get_service_url()
    assert url == "https://acquire.example.org"

    identity_url = get_service_url(service="identity", https=False)

    assert identity_url == "acquire.example.org/t/identity"

    identity_url = get_service_url(service="identity", https=True)

    assert identity_url == "https://acquire.example.org/t/identity"

