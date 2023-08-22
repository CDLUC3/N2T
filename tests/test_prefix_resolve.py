
import pytest
import lib_n2t.prefixes


def get_prefix_test_case():
    src = "data/prefixes.json"
    prefixes = lib_n2t.prefixes.PrefixList(fn_src=src)
    for prefix in prefixes.prefixes():
        test = f"{prefix}:foo:332#2@!/\\.,;---_=+"
        expected = prefix
        yield test, prefix, prefixes


@pytest.mark.parametrize("inp,expected,resolver", get_prefix_test_case())
def test_resolve_prefix(inp, expected, resolver):
    """Checks that a resolver is found given an identifier
    """
    scheme, value = lib_n2t.get_scheme(inp)
    res = resolver.get_resolver(inp)
    assert len(res) > 0
    _found = False
    for r in res:
        if not _found and r.get("id") == scheme:
            _found = True
    assert _found
    #assert res['id'] == expected
    #print(res)
    #print(f"input = {inp}, expected = {expected}, {res['id']}")

