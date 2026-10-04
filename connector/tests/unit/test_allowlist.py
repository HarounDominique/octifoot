import pytest

from spiderfoot_connector.allowlist import is_allowed, parse_allowlist

AL = frozenset({"example.com"})


@pytest.mark.parametrize(
    "target",
    ["example.com", "EXAMPLE.com", "example.com.", "www.example.com", "a.b.example.com"],
)
def test_allowed(target):
    assert is_allowed(target, AL)


@pytest.mark.parametrize(
    "target",
    ["evilexample.com", "example.com.evil.org", "example.org", "com", "", "  "],
)
def test_not_allowed(target):
    assert not is_allowed(target, AL)


def test_empty_allowlist_allows_nothing():
    assert not is_allowed("example.com", frozenset())


def test_parse_allowlist_normalizes():
    assert parse_allowlist(" Example.com, ,foo.org. ") == frozenset({"example.com", "foo.org"})


def test_parse_allowlist_empty():
    assert parse_allowlist("") == frozenset()
    assert parse_allowlist(None) == frozenset()
