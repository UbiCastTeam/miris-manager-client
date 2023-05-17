import json
from unittest.mock import patch

CONFIG = {
    'SERVER_URL': 'https://mmctest',
    'SECRET_KEY': 'the secret key',
    'API_KEY': 'test API key',
}


class MockResponse:
    def __init__(self, json_data, status_code):
        self.text = json.dumps(json_data)
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def mocked_request(*args, **kwargs):
    url = kwargs['url']
    if url == CONFIG['SERVER_URL'] + '/api/':
        return MockResponse({'version': '8.0.0'}, 200)
    if url == CONFIG['SERVER_URL'] + '/api/v3/fleet/control/set-command-status/':
        return MockResponse({}, 200)
    if url == CONFIG['SERVER_URL'] + '/remote-event/v3':
        from mm_client.lib.signing import get_signature
        data = get_signature(CONFIG)
        data.update({
            'uid': 'test_uid',
            'action': 'START_RECORDING',
            'params': {'channel': 'Chan'},
        })
        return MockResponse(data, 200)
    print(f'Non mocked URL: {url}')
    return MockResponse(None, 404)


@patch('requests.post', side_effect=mocked_request)
@patch('requests.get', side_effect=mocked_request)
def test_client(mock_get, mock_post):
    from mm_client.client import MirisManagerClient
    mmc = MirisManagerClient(local_conf=CONFIG)
    response = mmc.api_request('PING')
    assert isinstance(response, dict)
    assert response['version'] == '8.0.0'

    assert len(mock_get.call_args_list) == 1
    assert len(mock_post.call_args_list) == 0


@patch('requests.post', side_effect=mocked_request)
@patch('requests.get', side_effect=mocked_request)
def test_long_polling(mock_get, mock_post):
    from mm_client.client import MirisManagerClient

    commands = []

    class LongPollingClient(MirisManagerClient):
        DEFAULT_CONF = CONFIG

        def handle_action(self, uid, action, params):
            commands.append((uid, action, params))
            return 'DONE', ''

    mmc = LongPollingClient(local_conf=CONFIG)
    mmc.long_polling_loop(single_loop=True)

    assert len(mock_get.call_args_list) == 1
    assert len(mock_post.call_args_list) == 1
    call = mock_post.call_args_list[0]
    assert call.kwargs['data'] == {'uid': 'test_uid', 'status': 'DONE', 'data': ''}

    assert commands == [('test_uid', 'START_RECORDING', {'channel': 'Chan'})]
