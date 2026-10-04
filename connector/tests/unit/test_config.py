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


# --- address of the SpiderFoot UI for links from OpenCTI ---


def test_ui_url_defaults_to_no_links():
    assert load_settings(BASE).ui_url == ""


def test_ui_url_is_read_and_loses_its_trailing_slash():
    assert (
        load_settings({**BASE, "SPIDERFOOT_UI_URL": "http://localhost:5001/"}).ui_url
        == "http://localhost:5001"
    )
    assert (
        load_settings({**BASE, "SPIDERFOOT_UI_URL": "https://sf.example.net"}).ui_url
        == "https://sf.example.net"
    )


def test_blank_ui_url_means_no_links():
    assert load_settings({**BASE, "SPIDERFOOT_UI_URL": "  "}).ui_url == ""


@pytest.mark.parametrize(
    "bad", ["localhost:5001", "ftp://sf:5001", "javascript:alert(1)", "http://"]
)
def test_ui_url_must_be_http_or_https_with_a_host(bad):
    with pytest.raises(ConfigError, match="SPIDERFOOT_UI_URL"):
        load_settings({**BASE, "SPIDERFOOT_UI_URL": bad})


# --- automatic re-analysis of watched domains ---


def test_watch_is_off_by_default():
    s = load_settings(BASE)
    assert s.watch_interval_minutes == 0 and s.watch_max_per_cycle == 3


def test_watch_interval_and_cap_are_read():
    s = load_settings(
        {**BASE, "SPIDERFOOT_WATCH_INTERVAL_MINUTES": "1440", "SPIDERFOOT_WATCH_MAX_PER_CYCLE": "5"}
    )
    assert s.watch_interval_minutes == 1440 and s.watch_max_per_cycle == 5


@pytest.mark.parametrize("bad", ["1", "4", "10081", "-5", "soon"])
def test_watch_interval_must_be_zero_or_between_five_minutes_and_a_week(bad):
    with pytest.raises(ConfigError, match="SPIDERFOOT_WATCH_INTERVAL_MINUTES"):
        load_settings({**BASE, "SPIDERFOOT_WATCH_INTERVAL_MINUTES": bad})


@pytest.mark.parametrize("bad", ["0", "21"])
def test_watch_cap_is_bounded(bad):
    with pytest.raises(ConfigError, match="SPIDERFOOT_WATCH_MAX_PER_CYCLE"):
        load_settings({**BASE, "SPIDERFOOT_WATCH_MAX_PER_CYCLE": bad})


# --- the allowlist in .env is validated like the control panel's ---


@pytest.mark.parametrize(
    "bad",
    [
        "com",
        "co.uk",
        "192.168.0.1",
        "http://example.com",
        "*.example.com",
        "example.com/path",
        "localhost",
    ],
)
def test_an_unsafe_allowlist_entry_refuses_to_start_and_names_it(bad):
    with pytest.raises(ConfigError) as err:
        load_settings({**BASE, "SPIDERFOOT_ALLOWED_DOMAINS": f"example.com,{bad}"})
    assert "SPIDERFOOT_ALLOWED_DOMAINS" in str(err.value) and bad in str(err.value)


def test_valid_entries_keep_working_and_are_normalised():
    s = load_settings(
        {**BASE, "SPIDERFOOT_ALLOWED_DOMAINS": " Example.COM. , forocoches.com ,www.example.org"}
    )
    assert s.allowed_domains == frozenset({"example.com", "forocoches.com", "www.example.org"})


# --- control panel settings ---

UI_TOKEN = "SENTINEL-UI-TOKEN-0123456789"


def panel_env(**extra):
    return {
        **BASE,
        "OCTIFOOT_STATE_DIR": "/var/lib/octifoot",
        "OCTIFOOT_UI_TOKEN": UI_TOKEN,
        **extra,
    }


def test_the_panel_is_off_by_default_with_safe_defaults():
    s = load_settings(BASE)
    assert s.ui_token == "" and s.ui_port == 8099 and s.ui_bind == "127.0.0.1" and s.ui_lang == "en"


def test_a_token_enables_the_panel_when_a_state_directory_is_given():
    s = load_settings(panel_env())
    assert s.ui_token == UI_TOKEN and s.state_dir == "/var/lib/octifoot"


def test_the_token_never_shows_in_the_settings_repr():
    assert UI_TOKEN not in repr(load_settings(panel_env())) and UI_TOKEN not in str(
        load_settings(panel_env())
    )


@pytest.mark.parametrize("short", ["x", "a" * 15])
def test_a_short_token_is_refused_without_echoing_it(short):
    with pytest.raises(ConfigError) as err:
        load_settings(panel_env(OCTIFOOT_UI_TOKEN=short))
    assert "OCTIFOOT_UI_TOKEN" in str(err.value) and "16" in str(err.value)


def test_the_panel_needs_a_state_directory():
    with pytest.raises(ConfigError, match="OCTIFOOT_STATE_DIR"):
        load_settings({**BASE, "OCTIFOOT_UI_TOKEN": UI_TOKEN})


@pytest.mark.parametrize("bad", ["0", "65536", "-1", "http", ""])
def test_the_panel_port_must_be_a_valid_port(bad):
    if bad == "":
        assert load_settings(panel_env(OCTIFOOT_UI_PORT=bad)).ui_port == 8099
        return
    with pytest.raises(ConfigError, match="OCTIFOOT_UI_PORT"):
        load_settings(panel_env(OCTIFOOT_UI_PORT=bad))


def test_the_panel_port_and_language_are_read():
    s = load_settings(panel_env(OCTIFOOT_UI_PORT="9000", OCTIFOOT_UI_LANG="es"))
    assert s.ui_port == 9000 and s.ui_lang == "es"


def test_an_unknown_language_is_refused():
    with pytest.raises(ConfigError, match="OCTIFOOT_UI_LANG"):
        load_settings(panel_env(OCTIFOOT_UI_LANG="fr"))


@pytest.mark.parametrize("good", ["127.0.0.1", "0.0.0.0", "::1"])
def test_the_bind_address_must_be_an_ip(good):
    assert load_settings(panel_env(OCTIFOOT_UI_BIND=good)).ui_bind == good


@pytest.mark.parametrize("bad", ["localhost", "example.com", "300.1.1.1"])
def test_a_bind_address_that_is_not_an_ip_is_refused(bad):
    with pytest.raises(ConfigError, match="OCTIFOOT_UI_BIND"):
        load_settings(panel_env(OCTIFOOT_UI_BIND=bad))
