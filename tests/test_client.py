import json
from unittest.mock import patch

CONFIG = {
    'SERVER_URL': 'https://mmctest'
}


def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.text = json.dumps(json_data)
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

    if kwargs['url'] == CONFIG['SERVER_URL'] + '/api/':
        return MockResponse({'version': '8.0.0'}, 200)

    return MockResponse(None, 404)


@patch('requests.get', side_effect=mocked_requests_get)
def test_client(mock_get):
    from mm_client.client import MirisManagerClient
    mmc = MirisManagerClient(local_conf=CONFIG)
    response = mmc.api_request('PING')
    assert isinstance(response, dict)
    assert response['version'] == '8.0.0'

    assert len(mock_get.call_args_list) == 1
