import os.path
import pytest

import lib_n2t.pidconfig


DATA_PATH = os.path.join(os.path.dirname(__file__), "data")

def test_config():
    conf = lib_n2t.pid_config.PidConfig("config_01.json", base_path=DATA_PATH)
    assert conf.target == "{pid}"
    assert conf.keys == ["test", ]
    sub_conf = conf.get_entry("test")
    assert sub_conf.target == "{group_value_raw}"
