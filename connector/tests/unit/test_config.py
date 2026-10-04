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


def test_expansion_disabled_by_default():
    s = load_settings(BASE)
    assert s.max_depth == 0
    assert s.max_scans == 5


def test_expansion_settings_parsed():
    s = load_settings({**BASE, "SPIDERFOOT_MAX_DEPTH": "2", "SPIDERFOOT_MAX_SCANS": "8"})
    assert (s.max_depth, s.max_scans) == (2, 8)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("SPIDERFOOT_MAX_DEPTH", "4"),
        ("SPIDERFOOT_MAX_DEPTH", "-1"),
        ("SPIDERFOOT_MAX_SCANS", "0"),
        ("SPIDERFOOT_MAX_SCANS", "21"),
        ("SPIDERFOOT_MAX_DEPTH", "x"),
    ],
)
def test_expansion_bounds_enforced(key, value):
    with pytest.raises(ConfigError, match=key):
        load_settings({**BASE, key: value})


def test_profile_defaults_to_lean_with_passive_usecase():
    assert load_settings(BASE).profile == "lean"


def test_profile_defaults_to_full_when_usecase_is_not_passive():
    env = {**BASE, "SPIDERFOOT_USECASE": "footprint", "SPIDERFOOT_ALLOW_ACTIVE": "true"}
    assert load_settings(env).profile == "full"


def test_full_profile_can_still_be_selected():
    assert load_settings({**BASE, "SPIDERFOOT_PROFILE": "full"}).profile == "full"


def test_lean_profile_accepted_with_passive():
    assert load_settings({**BASE, "SPIDERFOOT_PROFILE": "lean"}).profile == "lean"


def test_unknown_profile_rejected():
    with pytest.raises(ConfigError, match="SPIDERFOOT_PROFILE"):
        load_settings({**BASE, "SPIDERFOOT_PROFILE": "turbo"})


def test_lean_requires_passive_usecase():
    env = {
        **BASE,
        "SPIDERFOOT_PROFILE": "lean",
        "SPIDERFOOT_USECASE": "all",
        "SPIDERFOOT_ALLOW_ACTIVE": "true",
    }
    with pytest.raises(ConfigError, match="lean"):
        load_settings(env)
