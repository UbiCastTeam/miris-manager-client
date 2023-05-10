import datetime

import pytest


def test_signature__default():
    from mm_client.client import MirisManagerClient
    from mm_client.lib.signing import get_signature, check_signature

    client = MirisManagerClient()

    signature = get_signature(client)
    assert signature == {}

    assert check_signature(client, {}) is None


def test_signature__configured():
    from mm_client.client import MirisManagerClient
    from mm_client.lib.signing import get_signature, check_signature

    conf = {
        'SECRET_KEY': 'the secret key',
        'API_KEY': 'the API key',
    }
    client = MirisManagerClient(conf)

    signature = get_signature(client)
    assert sorted(signature.keys()) == ['hmac', 'time']

    assert check_signature(client, signature) is None


@pytest.mark.parametrize('signature, expected', [
    pytest.param(
        {},
        'some mandatory data are missing.',
        id='missing'),
    pytest.param(
        {'time': 'invalid', 'hmac': 'test'},
        'the received time is invalid.',
        id='date'),
    pytest.param(
        {'time': '2000-01-01_00-00-00_000', 'hmac': 'test'},
        'the difference between the request time and the current time is too large.',
        id='expired'),
    pytest.param(
        {'time': datetime.datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S_%f'), 'hmac': 'test'},
        'the received and computed HMAC values do not match.',
        id='hmac'),
])
def test_signature__invalid(signature, expected):
    from mm_client.client import MirisManagerClient
    from mm_client.lib.signing import check_signature

    conf = {
        'SECRET_KEY': 'the secret key',
        'API_KEY': 'the API key',
    }
    client = MirisManagerClient(conf)

    assert check_signature(client, signature) == expected
