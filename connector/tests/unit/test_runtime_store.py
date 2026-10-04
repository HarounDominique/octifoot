import json
from datetime import UTC, datetime

import pytest

from spiderfoot_connector.runtime import MAX_UI_DOMAINS, RuntimeStore

NOW = datetime(2026, 10, 4, 12, 0, 0, tzinfo=UTC)
TOKEN = "SENTINEL-TOKEN-0123456789abcdef"


@pytest.fixture
def store(tmp_path):
    return RuntimeStore(tmp_path / "state", clock=lambda: NOW)


def audit_lines(store):
    path = store.directory / "audit.log"
    return path.read_text().splitlines() if path.exists() else []


# --- domains ---


def test_a_new_store_is_empty_and_creates_its_directory(store):
    assert store.domains() == [] and store.timeout_override() is None and store.problem is None
    assert store.directory.is_dir()


def test_an_added_domain_is_normalised_stored_and_persisted(store):
    assert store.add_domain("  WWW.Example.COM. ", by="127.0.0.1") == "www.example.com"
    again = RuntimeStore(store.directory, clock=lambda: NOW)
    assert [d["value"] for d in again.domains()] == ["www.example.com"]
    assert again.domains()[0]["added_at"] == "2026-10-04T12:00:00Z"


def test_an_invalid_domain_is_refused_and_nothing_is_stored(store):
    with pytest.raises(ValueError, match="at least two"):
        store.add_domain("com", by="127.0.0.1")
    assert store.domains() == []


def test_a_duplicate_is_refused(store):
    store.add_domain("example.com", by="127.0.0.1")
    with pytest.raises(ValueError, match="already"):
        store.add_domain("EXAMPLE.com.", by="127.0.0.1")


def test_the_number_of_added_domains_is_capped(store):
    for i in range(MAX_UI_DOMAINS):
        store.add_domain(f"site{i}.example.com", by="127.0.0.1")
    with pytest.raises(ValueError, match="limit"):
        store.add_domain("one-more.example.com", by="127.0.0.1")


def test_a_domain_can_be_removed_and_removal_persists(store):
    store.add_domain("a.example.com", by="127.0.0.1")
    store.add_domain("b.example.com", by="127.0.0.1")
    store.remove_domain("A.example.com", by="127.0.0.1")
    assert [d["value"] for d in RuntimeStore(store.directory).domains()] == ["b.example.com"]


def test_removing_a_domain_that_is_not_there_is_an_error(store):
    with pytest.raises(ValueError, match="not in the list"):
        store.remove_domain("ghost.example.com", by="127.0.0.1")


# --- maximum time ---


@pytest.mark.parametrize("seconds", [60, 900, 1800, 7200])
def test_valid_timeouts_are_stored(store, seconds):
    store.set_timeout(seconds, by="127.0.0.1")
    assert RuntimeStore(store.directory).timeout_override() == seconds


@pytest.mark.parametrize("bad", [59, 7201, 0, -5, "abc", "", 12.5, True])
def test_out_of_range_or_malformed_timeouts_are_refused(store, bad):
    with pytest.raises(ValueError, match="between 60 and 7200"):
        store.set_timeout(bad, by="127.0.0.1")
    assert store.timeout_override() is None


def test_a_numeric_string_is_accepted(store):
    store.set_timeout("1800", by="127.0.0.1")
    assert store.timeout_override() == 1800


def test_clearing_the_timeout_returns_to_the_default(store):
    store.set_timeout(1800, by="127.0.0.1")
    store.set_timeout(None, by="127.0.0.1")
    assert store.timeout_override() is None


# --- effective values ---


def test_effective_allowlist_is_the_env_list_plus_the_added_ones(store):
    store.add_domain("added.example.com", by="127.0.0.1")
    assert store.effective_allowlist(frozenset({"env.example.com"})) == frozenset(
        {"env.example.com", "added.example.com"}
    )


def test_a_removed_domain_leaves_the_effective_list_immediately(store):
    store.add_domain("added.example.com", by="127.0.0.1")
    store.remove_domain("added.example.com", by="127.0.0.1")
    assert store.effective_allowlist(frozenset({"env.example.com"})) == frozenset(
        {"env.example.com"}
    )


def test_the_env_list_cannot_be_removed_through_the_store(store):
    with pytest.raises(ValueError, match="not in the list"):
        store.remove_domain("env.example.com", by="127.0.0.1")


def test_effective_timeout_prefers_the_override_then_the_env_value(store):
    assert store.effective_timeout(900) == 900
    store.set_timeout(1800, by="127.0.0.1")
    assert store.effective_timeout(900) == 1800


# --- audit ---


def test_every_change_is_audited_with_time_action_value_and_client(store):
    store.add_domain("a.example.com", by="127.0.0.1")
    store.set_timeout(1800, by="127.0.0.1")
    store.remove_domain("a.example.com", by="127.0.0.1")
    lines = audit_lines(store)
    assert len(lines) == 3
    assert lines[0] == "2026-10-04T12:00:00Z add domain=a.example.com by=127.0.0.1"
    assert lines[1] == "2026-10-04T12:00:00Z timeout seconds=1800 by=127.0.0.1"
    assert lines[2] == "2026-10-04T12:00:00Z remove domain=a.example.com by=127.0.0.1"


def test_refused_changes_are_not_audited_as_if_they_happened(store):
    with pytest.raises(ValueError):
        store.add_domain("com", by="127.0.0.1")
    assert audit_lines(store) == []


def test_a_client_string_with_control_characters_cannot_forge_audit_lines(store):
    store.add_domain("a.example.com", by="1.2.3.4\n2026-01-01T00:00:00Z add domain=evil.com by=x")
    lines = audit_lines(store)
    assert len(lines) == 1 and "\n" not in lines[0]


# --- robustness ---


def test_a_corrupt_state_file_is_treated_as_empty_and_reported(tmp_path):
    directory = tmp_path / "state"
    directory.mkdir()
    (directory / "settings.json").write_text("{not json")
    store = RuntimeStore(directory)
    assert store.domains() == [] and store.timeout_override() is None
    assert store.problem and "settings.json" in store.problem
    assert store.effective_allowlist(frozenset({"env.example.com"})) == frozenset(
        {"env.example.com"}
    )
    assert store.effective_timeout(900) == 900


def test_a_state_file_with_a_wrong_shape_is_treated_as_corrupt(tmp_path):
    directory = tmp_path / "state"
    directory.mkdir()
    (directory / "settings.json").write_text(json.dumps({"domains": "not a list"}))
    assert RuntimeStore(directory).problem


def test_a_hand_edited_invalid_domain_in_the_file_is_ignored_not_authorised(tmp_path):
    directory = tmp_path / "state"
    directory.mkdir()
    (directory / "settings.json").write_text(
        json.dumps(
            {
                "domains": [
                    {"value": "com", "added_at": "x"},
                    {"value": "ok.example.com", "added_at": "x"},
                ]
            }
        )
    )
    store = RuntimeStore(directory)
    assert store.effective_allowlist(frozenset()) == frozenset({"ok.example.com"})


def test_writes_are_atomic_and_leave_no_temporary_file(store):
    store.add_domain("a.example.com", by="127.0.0.1")
    names = sorted(p.name for p in store.directory.iterdir())
    assert names == ["audit.log", "settings.json"]
    json.loads((store.directory / "settings.json").read_text())


def test_the_token_is_never_written_to_state_or_audit(store):
    store.add_domain("a.example.com", by="127.0.0.1")
    for path in store.directory.iterdir():
        assert TOKEN not in path.read_text()
