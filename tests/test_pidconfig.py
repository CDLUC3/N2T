import os.path
import pytest

import lib_n2t.pidconfig


DATA_PATH = os.path.join(os.path.dirname(__file__), "test_data")

def test_config():
    conf = lib_n2t.pidconfig.PidConfig("config_01.json", base_path=DATA_PATH)
    assert conf.target == "{pid}"
    assert list(conf.keys) == ["test", ]
    sub_conf, _ = conf.get_entry("test")
    assert sub_conf.target == "{group_value_raw}"
