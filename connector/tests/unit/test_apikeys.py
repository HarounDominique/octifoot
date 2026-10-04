import json

import pytest

from spiderfoot_connector.apikeys import KeyRing, apply_keys, load_keyring
from spiderfoot_connector.config import ConfigError

SECRET = "SENTINEL-KEY-VALUE-123"

SNAPSHOT = {
    "sfp_keyed": {
        "flags": ["apikey"],
        "useCases": ["Passive"],
        "produced": ["IP_ADDRESS"],
        "watched": ["*"],
    },
    "sfp_keyed2": {
        "flags": ["apikey"],
        "useCases": ["Passive"],
        "produced": ["IP_ADDRESS"],
        "watched": ["*"],
    },
    "sfp_plain": {"flags": [], "useCases": ["Passive"], "produced": [], "watched": ["*"]},
    "sfp_active": {
        "flags": ["apikey", "invasive"],
        "useCases": ["Footprint"],
        "produced": [],
        "watched": ["*"],
    },
    "sfp_tool": {
        "flags": ["apikey", "tool"],
        "useCases": ["Footprint"],
        "produced": [],
        "watched": ["*"],
    },
}


def write(tmp_path, content):
    p = tmp_path / "keys.json"
    p.write_text(content if isinstance(content, str) else json.dumps(content))
    return str(p)


# --- parsing and validation ---


def test_a_bare_module_name_means_its_api_key_option(tmp_path):
    ring = load_keyring(write(tmp_path, {"sfp_keyed": SECRET}), SNAPSHOT)
    assert ring.entries == {"sfp_keyed:api_key": SECRET}
    assert ring.modules == frozenset({"sfp_keyed"})


def test_an_explicit_module_option_name_is_used_as_written(tmp_path):
    ring = load_keyring(write(tmp_path, {"sfp_keyed:other_api_key": SECRET}), SNAPSHOT)
    assert ring.entries == {"sfp_keyed:other_api_key": SECRET}


def test_several_modules_are_loaded(tmp_path):
    ring = load_keyring(write(tmp_path, {"sfp_keyed": "a1", "sfp_keyed2": "b2"}), SNAPSHOT)
    assert ring.modules == frozenset({"sfp_keyed", "sfp_keyed2"})


@pytest.mark.parametrize(
    ("content", "needle"),
    [
        ("{not json", "valid JSON"),
        ('["a", "b"]', "JSON object"),
        ('"just a string"', "JSON object"),
        ({"sfp_keyed": ""}, "sfp_keyed"),
        ({"sfp_keyed": "   "}, "sfp_keyed"),
        ({"sfp_keyed": 12345}, "sfp_keyed"),
        ({"sfp_keyed": "x" * 513}, "sfp_keyed"),
        ({"sfp_keyed": "ab\ncd"}, "sfp_keyed"),
        ({"sfp_keyed": "ab\x00cd"}, "sfp_keyed"),
        ({"sfp_nope": SECRET}, "sfp_nope"),
        ({"sfp_plain": SECRET}, "sfp_plain"),
        ({"sfp_active": SECRET}, "sfp_active"),
        ({"sfp_tool": SECRET}, "sfp_tool"),
        ({"sfp_keyed:": SECRET}, "sfp_keyed:"),
        ({":api_key": SECRET}, ":api_key"),
    ],
)
def test_invalid_files_fail_fast_naming_the_entry_and_never_the_value(tmp_path, content, needle):
    with pytest.raises(ConfigError) as err:
        load_keyring(write(tmp_path, content), SNAPSHOT)
    assert needle in str(err.value)
    assert SECRET not in str(err.value)


def test_a_missing_file_fails_fast(tmp_path):
    with pytest.raises(ConfigError, match="SPIDERFOOT_API_KEYS_FILE"):
        load_keyring(str(tmp_path / "absent.json"), SNAPSHOT)


def test_a_directory_instead_of_a_file_fails_fast(tmp_path):
    with pytest.raises(ConfigError, match="SPIDERFOOT_API_KEYS_FILE"):
        load_keyring(str(tmp_path), SNAPSHOT)


def test_an_empty_object_is_a_valid_empty_ring(tmp_path):
    ring = load_keyring(write(tmp_path, {}), SNAPSHOT)
    assert ring.entries == {} and ring.modules == frozenset()


def test_the_value_is_stripped_of_surrounding_whitespace(tmp_path):
    ring = load_keyring(write(tmp_path, {"sfp_keyed": f"  {SECRET}\n"}), SNAPSHOT)
    assert ring.entries["sfp_keyed:api_key"] == SECRET


def test_the_ring_never_shows_values_when_printed():
    ring = KeyRing({"sfp_keyed:api_key": SECRET})
    assert SECRET not in repr(ring) and SECRET not in str(ring)
    assert "sfp_keyed" in repr(ring)


# --- applying keys to SpiderFoot, verifying what was stored ---


class FakeSpiderFoot:
    """Mimics SpiderFoot v4.0: options are read as module.<m>.<o>, written as <m>:<o>, and any other
    write name returns success while changing nothing."""

    def __init__(self, options, *, drop_value_chars=False, fail_save=False):
        self.data = dict(options)
        self.tokens = 0
        self.drop = drop_value_chars
        self.fail_save = fail_save
        self.saved = []

    def get_options(self):
        self.tokens += 1
        return f"token-{self.tokens}", dict(self.data)

    def save_options(self, options, token):
        assert token == f"token-{self.tokens}", "must use the freshest token"
        if self.fail_save:
            raise RuntimeError("SpiderFoot settings API unavailable")
        self.saved.append(dict(options))
        for name, value in options.items():
            module, _, option = name.partition(":")
            key = f"module.{module}.{option}"
            if ":" in name and key in self.data:
                self.data[key] = value[:3] if self.drop else value


def fake(**kw):
    return FakeSpiderFoot({"module.sfp_keyed.api_key": "", "module.sfp_keyed2.api_key": ""}, **kw)


def test_a_key_is_written_with_the_colon_name_and_verified_by_reading_it_back():
    sf = fake()
    result = apply_keys(KeyRing({"sfp_keyed:api_key": SECRET}), sf)
    assert result.applied == frozenset({"sfp_keyed"}) and result.failed == []
    assert sf.saved == [{"sfp_keyed:api_key": SECRET}]
    assert sf.data["module.sfp_keyed.api_key"] == SECRET


def test_every_key_is_applied_with_a_fresh_token_each():
    sf = fake()
    result = apply_keys(KeyRing({"sfp_keyed:api_key": "a1", "sfp_keyed2:api_key": "b2"}), sf)
    assert result.applied == frozenset({"sfp_keyed", "sfp_keyed2"}) and len(sf.saved) == 2


def test_a_key_already_stored_is_not_written_again():
    sf = FakeSpiderFoot({"module.sfp_keyed.api_key": SECRET})
    result = apply_keys(KeyRing({"sfp_keyed:api_key": SECRET}), sf)
    assert result.applied == frozenset({"sfp_keyed"}) and sf.saved == []


def test_an_option_that_does_not_exist_is_reported_and_never_written():
    sf = fake()
    result = apply_keys(KeyRing({"sfp_keyed:no_such_option": SECRET}), sf)
    assert result.applied == frozenset() and result.failed == ["sfp_keyed:no_such_option"]
    assert sf.saved == []


def test_a_value_that_spiderfoot_stores_differently_is_dropped_not_trusted():
    sf = fake(drop_value_chars=True)
    result = apply_keys(KeyRing({"sfp_keyed:api_key": SECRET}), sf)
    assert result.applied == frozenset() and result.failed == ["sfp_keyed:api_key"]


def test_one_bad_key_does_not_stop_the_others():
    sf = fake()
    ring = KeyRing({"sfp_keyed:nope": "x", "sfp_keyed2:api_key": "b2"})
    result = apply_keys(ring, sf)
    assert result.applied == frozenset({"sfp_keyed2"}) and result.failed == ["sfp_keyed:nope"]


def test_a_failing_settings_api_drops_every_key_without_raising():
    sf = fake(fail_save=True)
    result = apply_keys(KeyRing({"sfp_keyed:api_key": SECRET, "sfp_keyed2:api_key": "b2"}), sf)
    assert result.applied == frozenset()
    assert sorted(result.failed) == ["sfp_keyed2:api_key", "sfp_keyed:api_key"]


def test_an_unreachable_options_endpoint_drops_every_key_without_raising():
    class Down:
        def get_options(self):
            raise RuntimeError("down")

        def save_options(self, options, token):
            raise AssertionError("must not be called")

    result = apply_keys(KeyRing({"sfp_keyed:api_key": SECRET}), Down())
    assert result.applied == frozenset() and result.failed == ["sfp_keyed:api_key"]


def test_failures_name_the_option_and_never_the_value():
    result = apply_keys(KeyRing({"sfp_keyed:nope": SECRET}), fake())
    assert SECRET not in repr(result) and SECRET not in " ".join(result.failed)
