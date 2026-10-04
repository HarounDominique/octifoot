import pytest

from spiderfoot_connector.config import ConfigError, load_settings

BASE = {
    "SPIDERFOOT_URL": "http://spiderfoot:5001",
    "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
}


def test_defaults_are_passive_and_safe():
    s = load_settings(BASE)
    assert s.usecase == "passive"
    assert s.allowed_domains == frozenset({"example.com"})
    assert s.timeout_seconds == 900
    assert s.score == 30
    assert s.base_url == "http://spiderfoot:5001"


def test_missing_allowlist_fails_fast():
    with pytest.raises(ConfigError, match="SPIDERFOOT_ALLOWED_DOMAINS"):
        load_settings({"SPIDERFOOT_URL": "http://x:5001"})


def test_blank_allowlist_fails_fast():
    with pytest.raises(ConfigError, match="SPIDERFOOT_ALLOWED_DOMAINS"):
        load_settings({**BASE, "SPIDERFOOT_ALLOWED_DOMAINS": " , "})


def test_missing_url_fails():
    with pytest.raises(ConfigError, match="SPIDERFOOT_URL"):
        load_settings({"SPIDERFOOT_ALLOWED_DOMAINS": "example.com"})


def test_url_trailing_slash_stripped():
    assert load_settings({**BASE, "SPIDERFOOT_URL": "http://x:5001/"}).base_url == "http://x:5001"


def test_active_usecase_requires_explicit_opt_in():
    with pytest.raises(ConfigError, match="SPIDERFOOT_ALLOW_ACTIVE"):
        load_settings({**BASE, "SPIDERFOOT_USECASE": "all"})
    s = load_settings({**BASE, "SPIDERFOOT_USECASE": "all", "SPIDERFOOT_ALLOW_ACTIVE": "true"})
    assert s.usecase == "all"


def test_unknown_usecase_rejected():
    with pytest.raises(ConfigError, match="SPIDERFOOT_USECASE"):
        load_settings({**BASE, "SPIDERFOOT_USECASE": "bogus"})


@pytest.mark.parametrize("key", ["SPIDERFOOT_TIMEOUT_SECONDS", "SPIDERFOOT_SCORE"])
def test_bad_numbers_rejected(key):
    with pytest.raises(ConfigError, match=key):
        load_settings({**BASE, key: "abc"})


def test_score_out_of_range_rejected():
    with pytest.raises(ConfigError, match="SPIDERFOOT_SCORE"):
        load_settings({**BASE, "SPIDERFOOT_SCORE": "101"})
