"""Test cases for CORS support by the web application.

Liberal CORS support is needed to enable in-browser programmatic use of
PID identified resources.
"""

import logging
import os

import fastapi.testclient
import pytest
import sqlalchemy

import n2t.__main__ as n2tmain

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
CONFIG_DB = os.path.join(THIS_FOLDER, "test.db")
N2T_JSON_DIR = os.path.abspath(os.path.join(THIS_FOLDER, "../schemes"))

L = logging.getLogger("__name__")


@pytest.fixture(scope="module")
def n2tapp():
    # The app instance is a global in n2t.app, so need to configure
    # the environment before loading the module to ensure the correct
    # settings are being used.

    os.environ["N2T_DB_CONNECTION_STRING"] = f"sqlite:///{CONFIG_DB}"
    os.environ["N2T_JSON_DIR"] = N2T_JSON_DIR

    # Now import the app
    import n2t.app

    # And configure the database engine
    config = n2t.app.app.state.settings
    engine = sqlalchemy.create_engine(config.db_connection_string, pool_pre_ping=True, echo=False)
    n2t.app.app.state.dbengine = engine

    # Load the schemes for further tests
    L.info("Loading resolver database using %s", os.environ["N2T_DB_CONNECTION_STRING"])
    L.info("Scheme folder = %s", config.json_dir)
    records = n2tmain.json_to_records(config.json_dir)
    _ = n2tmain.records_to_db(records, config.db_connection_string)
    # Yield the app for use in the scope of this module's tests
    yield n2t.app.app
    # cleanup, remove the config db
    os.unlink(CONFIG_DB)


def test_cors_headers(n2tapp):
    client = fastapi.testclient.TestClient(n2tapp, follow_redirects=False)
    headers = {
        "origin":"https://example.com/",
    }
    response = client.request("GET", "/", headers=headers)
    assert response.headers.get("access-control-allow-origin", None) == "*"
    # No origin in request -> no CORS
    response = client.request("GET", "/")
    assert response.headers.get("access-control-allow-origin", None) is None


ark_hyphen_tests = (
    ("/ark:99999/foo-bar", "https://arks.org/ark:99999/foo-bar"),
    ("/ark:99999/foobar", "https://arks.org/ark:99999/foobar"),
    ("/ark:/99999/foo-bar", "https://arks.org/ark:/99999/foo-bar"),
    ("/ark:/99999/foobar", "https://arks.org/ark:/99999/foobar"),
)

@pytest.mark.parametrize("inpid, expected", ark_hyphen_tests)
def test_ark_hyphens(n2tapp, inpid, expected):
    client = fastapi.testclient.TestClient(n2tapp, follow_redirects=False)
    response = client.request("GET", inpid)
    assert response.headers["location"] == expected


def identifier_test_cases():
    records = n2tmain.json_to_records(N2T_JSON_DIR)
    test_cases = []
    for k, record in records.items():
        _test = record.get("test", None)
        _probe = record.get("probe", None)
        if _test is not None and _probe is not None:
            if not _test.startswith(f"{k}:"):
                _test = f"{k}:{_test}"
            test_cases.append(
                pytest.param(
                    _test,
                    _probe,
                    id=k
                )
            )
    return test_cases

@pytest.mark.parametrize("test, probe", identifier_test_cases())
def test_identifier_resolutions(n2tapp, test, probe):
    client = fastapi.testclient.TestClient(n2tapp, follow_redirects=False)
    response = client.request("GET", f"/{test}")
    #print(f"RESPONSE = {response.headers}")
    target = response.headers.get("location")
    assert target == probe
