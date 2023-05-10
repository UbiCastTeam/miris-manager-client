from pathlib import Path

import pytest


@pytest.fixture()
def conf_path():
    path = Path('/tmp/mm-conf.json')
    path.write_text('{"SERVER_URL": "https://test"}')
    yield path
    path.unlink(missing_ok=True)


def test_conf_file__valid(conf_path):
    from mm_client.lib.configuration import load_conf, update_conf

    conf = load_conf(default_conf=conf_path)
    assert conf['SERVER_URL'] == 'https://test'

    updated = update_conf(conf_path, 'test', 'val')
    assert updated is True


def test_conf_file__does_not_exist(conf_path):
    from mm_client.lib.configuration import load_conf, update_conf

    conf_path.unlink()
    conf = load_conf(default_conf=conf_path)
    assert conf['SERVER_URL'] == 'https://mirismanager'

    updated = update_conf(conf_path, 'test', 'val')
    assert updated is True


def test_conf_dict():
    from mm_client.lib.configuration import load_conf, update_conf

    conf = load_conf(
        default_conf={'SERVER_URL': 'https://nope'},
        local_conf={'SERVER_URL': 'https://test'}
    )
    assert conf['SERVER_URL'] == 'https://test'

    updated = update_conf({'SERVER_URL': 'https://test'}, 'test', 'val')
    assert updated is False


def test_conf_default():
    from mm_client.lib.configuration import load_conf, update_conf

    conf = load_conf()
    assert conf['SERVER_URL'] == 'https://mirismanager'

    updated = update_conf(None, 'test', 'val')
    assert updated is False


@pytest.mark.parametrize('conf, is_valid', [
    pytest.param(
        {'SERVER_URL': 'https://mirismanager'},
        False,
        id='default'),
    pytest.param(
        {'SERVER_URL': 'https://test/'},
        True,
        id='valid'),
])
def test_conf_check(conf, is_valid):
    from mm_client.lib.configuration import check_conf

    if is_valid:
        check_conf(conf)
    else:
        with pytest.raises(ValueError):
            check_conf(conf)
