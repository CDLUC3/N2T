"""
This test script needs access to legacy n2t.

For each registered prefix that has a known test case, ensure that
the computed target is the same as the target returned by N2T.
"""
import json
import os.path
import pytest
import requests
import lib_n2t.model
import lib_n2t.pidconfig
import lib_n2t.pidparse
import lib_n2t.prefixes

DATA_PATH = os.path.join(os.path.dirname(__file__), "test_data")

session = requests.session()
pid_config = lib_n2t.pidconfig.PidConfig(os.path.join(DATA_PATH, "config.json"))

def get_prefix_test_case():
    with open(os.path.join(DATA_PATH, "prefixes.json"), "r") as src:
        prefixes = json.load(src)

    for k, v in prefixes.items():
        if v.get("type") == "scheme":
            testcase = v.get("test", None)
            if testcase is not None:
                # call N2T with constructed test and get Location
                pid_str = f"{k}:{testcase}"
                url = f"https://n2t.net/{pid_str}"
                yield pid_str, url


@pytest.mark.parametrize("pid_str,url", get_prefix_test_case())
def test_resolve_prefix(pid_str, url):
    """Checks that a resolver is found given an identifier
    """
    parser = lib_n2t.pidparse.BasePidParser(config=pid_config)
    pid = parser.parse(lib_n2t.model.ParsedPid(pid_str))
    response = session.get(url, allow_redirects=False)
    expected = response.headers.get("Location", None)

    print(f"{pid_str} : {expected} : {pid.target}")
    assert pid.target == expected

