

def test_get_host_info():
    from mm_client.lib.info import get_host_info

    expected = ['hostname', 'local_ip', 'mac']

    info = get_host_info(url='https://localhost')
    assert sorted(info.keys()) == expected
    for field in expected:
        assert info[field]


def test_get_free_space_bytes():
    from mm_client.lib.info import get_free_space_bytes

    remaining = get_free_space_bytes('/home')
    assert remaining > 0


def test_get_remaining_space():
    from mm_client.lib.info import get_remaining_space

    remaining = get_remaining_space()
    assert remaining > 0
