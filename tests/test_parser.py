import pytest
import rslv.lib_rslv.model
import lib_rslv.pidconfig
import lib_rslv.pidparse

config_ark = {
    "target": "https://arks.org/{group}/{value_raw}",
    "canonical": "{scheme}:{group_value}",
    "parser": "rslv.lib_rslv.pidparse.ArkParser",
    "data": {
        "12345": {
            "target": "https://example.org/ark/{group}/{value_raw}"
        },
        "12346": {
            "target": "https://example.org/{group}/{value}",
            "data": {},
        },
        "test": {
            "synonym_for": "99999"
        }
    }
}
config_doi = {
    "target": "https://doi.org/{group}/{value}",
    "canonical": "{scheme}:{group_value}",
    "parser": "lib_n2t.pidparse.DoiParser",
    "data": {}
}
config = {
    "target": "{pid}",
    "canonical": "{pid}",
    "parser": "lib_n2t.pidparse.BasePidParser",
    "data": {
        "general": {
            "target": "https://{scheme}.example.org/{group_value}",
            "data": {}
        },
        "group": {
            "target": "https://group.service/{scheme}:{group}/{value}",
            "parser": "lib_n2t.pidparse.GroupParser",
            "data": {}
        },
        "general_synonym": {
            "synonym_for": "general",
        },
        "ark": config_ark,
        "doi": config_doi,
    }
}

test_cases = [
    (
        "general:some-random-value",
        {"scheme": "general", "group_value": "some-random-value"},
    ),
    (
        "general_synonym:some-random-value",
        {"scheme": "general", "group_value": "some-random-value"},
    ),
    (
        "group:group_name/some-random-value",
        {
            "scheme": "group",
            "group_value": "group_name/some-random-value",
            "group": "group_name",
            "value": "some-random-value",
        },
    ),
    (
        "ark:",
        {
            "scheme": "ark",
            "group_value": None,
        },
    ),
    (
        "ark://99999/foo-bar/asngr;qorv;onqwr",
        {
            "scheme": "ark",
            "group_value": "99999/foobar/asngr;qorv;onqwr",
            "group": "99999",
            "group_raw": "99999",
            "value": "foobar/asngr;qorv;onqwr",
            "value_raw": "foo-bar/asngr;qorv;onqwr",
        }
    ),
    (
        "ark:/99999/foo-bar",
        {
            "scheme": "ark",
            "group_value": "99999/foobar",
            "group": "99999",
            "group_raw": "99999",
            "value": "foobar",
            "value_raw": "foo-bar",
        },
    ),
    (
        "ark:test/foo-bar",
        {
            "scheme": "ark",
            "group_value": "99999/foobar",
            "group": "99999",
            "group_raw": "99999",
            "value": "foobar",
            "value_raw": "foo-bar",
        },
    ),
    (
        "ark:12345/hyphen-target",
        {
            "scheme": "ark",
            "group_value": "12345/hyphentarget",
            "group": "12345",
            "group_raw": "12345",
            "value": "hyphentarget",
            "value_raw": "hyphen-target",
        },
    ),
    (
        "ark:12346/no-hyphen-target",
        {
            "scheme": "ark",
            "group_value": "12346/nohyphentarget",
            "group": "12346",
            "group_raw": "12346",
            "value": "nohyphentarget",
            "value_raw": "no-hyphen-target",
        },
    ),
    (
        "doi:10.1234/FOO-roo",
        {
            "scheme": "doi",
            "group_value": "10.1234/foo-roo",
            "group": "10.1234",
            "group_raw": "10.1234",
            "value": "foo-roo",
            "value_raw": "FOO-roo",
        }
    ),
]


pid_parser = lib_n2t.pidparse.BasePidParser(config=lib_n2t.pidconfig.PidConfig(config))


@pytest.mark.parametrize("pid,expected", test_cases)
def test_parsers(pid, expected):
    """
    Check properties of parsed pid align with expected

    Args:
        pid: identifier string
        expected: dict of expected values for parts of identifier
    """
    _pid = lib_n2t.model.ParsedPid(pid)
    result = pid_parser.parse(_pid)
    for k, v in expected.items():
        assert getattr(result, k) == v


template_cases = [
    (
        "ark:1234",
        None
    ),
    (
        "general:some-random-value",
        "https://general.example.org/some-random-value"
    ),
    (
        "group:group_name/some-random-value",
        "https://group.service/group:group_name/some-random-value"
    ),
    (
        "ark:/99999/foo-bar",
        "https://arks.org/99999/foo-bar",
    ),
    (
        "ark:test/foo-bar",
        "https://arks.org/99999/foo-bar",
    ),
    (
        "ark:12345/hyphen-target",
        "https://example.org/ark/12345/hyphen-target"
    ),
    (
        "ark:12346/no-hyphen-target",
        "https://example.org/12346/nohyphentarget"
    ),
    (
        "ark:",
        "ark:"
    ),
]


@pytest.mark.parametrize("pid,expected", template_cases)
def test_templates(pid, expected):
    _pid = lib_n2t.model.ParsedPid(pid)
    result = lib_n2t.pidparse.BasePidParser(config=lib_n2t.pidconfig.PidConfig(config)).parse(_pid)
    assert result.target == expected


canon_cases = [
    (
        "ark:1234",
        "ark:1234/"
    ),
    (
        "general:some-random-value",
        "general:some-random-value",
    ),
    (
        "group:group_name/some-random-value",
        "group:group_name/some-random-value",
    ),
    (
        "ark:/99999/foo-bar",
        "ark:99999/foobar",
    ),
    (
        "ark:12345/hyphen-target",
        "ark:12345/hyphentarget",
    ),
    (
        "ark:12346/no-hyphen-target",
        "ark:12346/nohyphentarget",
    ),
    (
        "ark:",
        "ark:"
    ),
    (
        "doi:10.2345/FOO/stuff/PEACH",
        "doi:10.2345/foo/stuff/peach",
    ),
    (
        "ark://99999/foo-bar/asngr;qorv;onqwr",
        "ark:99999/foobar/asngr;qorv;onqwr"
    ),
    (
        "ark://99999/wlter/foozle./",
        "ark:99999/wlter/foozle",
    ),
]
@pytest.mark.parametrize("pid,expected", canon_cases)
def test_canonical(pid, expected):
    _pid = lib_n2t.model.ParsedPid(pid)
    result = lib_n2t.pidparse.BasePidParser(config=lib_n2t.pidconfig.PidConfig(config)).parse(_pid)
    assert result.canonical == expected
