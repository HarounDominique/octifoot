import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spiderfoot_connector.client import ScanOutcome, SpiderFootError
from spiderfoot_connector.config import load_settings
from spiderfoot_connector.connector import SpiderFootEnrichment, TargetNotAllowed

EVENTS = json.loads((Path(__file__).parent.parent / "fixtures" / "scan_events.json").read_text())
SETTINGS = load_settings(
    {
        "SPIDERFOOT_URL": "http://sf:5001",
        "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
        "SPIDERFOOT_PROFILE": "full",
    }
)


def message(value="example.com", entity_type="Domain-Name"):
    return {"enrichment_entity": {"entity_type": entity_type, "observable_value": value}}


@pytest.fixture
def helper():
    return MagicMock()


def make(helper, outcome=None, error=None):
    client = MagicMock()
    if error:
        client.run_scan.side_effect = error
    else:
        client.run_scan.return_value = outcome or ScanOutcome("ABC123", "FINISHED", EVENTS)
    return SpiderFootEnrichment(helper, SETTINGS, client), client


def sent_bundle(helper):
    (bundle,), _ = helper.send_stix2_bundle.call_args
    return json.loads(bundle)


def test_refuses_target_outside_allowlist_without_scanning(helper):
    enrichment, client = make(helper)
    with pytest.raises(TargetNotAllowed, match="evilexample.com"):
        enrichment.process_message(message("evilexample.com"))
    client.run_scan.assert_not_called()
    helper.send_stix2_bundle.assert_not_called()


def test_refuses_non_domain_entity(helper):
    enrichment, client = make(helper)
    with pytest.raises(ValueError, match="Domain-Name"):
        enrichment.process_message(message(entity_type="IPv4-Addr"))
    client.run_scan.assert_not_called()


def test_happy_path_scans_passively_and_sends_bundle(helper):
    enrichment, client = make(helper)
    result = enrichment.process_message(message("www.example.com"))

    client.run_scan.assert_called_once_with(
        "www.example.com", "passive", timeout_seconds=900, poll_seconds=10
    )
    types = {o["type"] for o in sent_bundle(helper)["objects"]}
    assert {"domain-name", "ipv4-addr", "email-addr", "relationship", "note", "identity"} <= types
    assert "ABC123" in result and "FINISHED" in result


def test_timeout_is_flagged_in_result_message(helper):
    enrichment, _ = make(helper, ScanOutcome("ABC123", "RUNNING", EVENTS[:2], timed_out=True))
    assert "partial" in enrichment.process_message(message()).lower()
    helper.send_stix2_bundle.assert_called_once()


def test_failed_scan_raises_and_sends_nothing(helper):
    enrichment, _ = make(helper, ScanOutcome("ABC123", "ERROR-FAILED", []))
    with pytest.raises(SpiderFootError, match="ERROR-FAILED"):
        enrichment.process_message(message())
    helper.send_stix2_bundle.assert_not_called()


def test_client_error_propagates(helper):
    enrichment, _ = make(helper, error=SpiderFootError("boom"))
    with pytest.raises(SpiderFootError):
        enrichment.process_message(message())


def test_full_profile_does_not_pass_modules(helper):
    enrichment, client = make(helper)
    enrichment.process_message(message())
    assert "modules" not in client.run_scan.call_args.kwargs


def test_lean_profile_passes_the_derived_module_list(helper):
    from spiderfoot_connector.profiles import lean_modules

    lean = load_settings(
        {
            "SPIDERFOOT_URL": "http://sf:5001",
            "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
            "SPIDERFOOT_PROFILE": "lean",
        }
    )
    client = MagicMock()
    client.run_scan.return_value = ScanOutcome("ABC123", "FINISHED", EVENTS)
    SpiderFootEnrichment(helper, lean, client).process_message(message())
    modules = client.run_scan.call_args.kwargs["modules"]
    assert modules == lean_modules()
    assert "sfp_crt" in modules and "sfp_robtex" not in modules


# --- source health ---


def note_texts(helper):
    return [o["content"] for o in sent_bundle(helper)["objects"] if o["type"] == "note"]


def test_scan_errors_reach_the_scan_note(helper):
    enrichment, client = make(helper)
    client.fetch_errors.return_value = [("sfp_crobat_api", "Failed to retrieve content")]
    enrichment.process_message(message())
    client.fetch_errors.assert_called_once_with("ABC123")
    assert any("sfp_crobat_api: Failed to retrieve content (1)" in t for t in note_texts(helper))


def test_failing_log_read_does_not_fail_the_enrichment(helper):
    enrichment, client = make(helper)
    client.fetch_errors.side_effect = SpiderFootError("scanlog unavailable")
    enrichment.process_message(message())
    helper.send_stix2_bundle.assert_called_once()
    assert not any("Sources that reported errors" in t for t in note_texts(helper))


def test_no_scan_errors_means_no_health_line(helper):
    enrichment, client = make(helper)
    client.fetch_errors.return_value = []
    enrichment.process_message(message())
    assert not any("Sources that reported errors" in t for t in note_texts(helper))


# --- own DNS checks ---


def make_with_dns(helper, dns_check, settings=SETTINGS):
    client = MagicMock()
    client.run_scan.return_value = ScanOutcome("ABC123", "FINISHED", EVENTS)
    client.fetch_errors.return_value = []
    return SpiderFootEnrichment(helper, settings, client, dns_check=dns_check), client


def test_dns_checks_run_for_the_root_target_and_reach_the_note(helper):
    from spiderfoot_connector.dnschecks import DnsFacts

    asked = []

    def dns_check(name):
        asked.append(name)
        return DnsFacts(mx=[], spf="", dmarc="", caa=[], ds=[], mta_sts="")

    enrichment, _ = make_with_dns(helper, dns_check)
    enrichment.process_message(message("example.com"))
    assert asked == ["example.com"]
    assert any("DNS checks (queried by octifoot" in t for t in note_texts(helper))


def test_a_failing_dns_check_never_fails_the_enrichment(helper):
    def dns_check(name):
        raise RuntimeError("resolver exploded")

    enrichment, _ = make_with_dns(helper, dns_check)
    enrichment.process_message(message("example.com"))
    helper.send_stix2_bundle.assert_called_once()
    assert not any("DNS checks (queried" in t for t in note_texts(helper))


def test_no_dns_check_configured_means_no_dns_line(helper):
    enrichment, _ = make(helper)
    enrichment.process_message(message())
    assert not any("DNS checks (queried" in t for t in note_texts(helper))


# --- an incomplete scan says so in its Note ---


def test_timeout_is_stated_in_the_note_not_only_in_the_work_message(helper):
    enrichment, client = make(helper, ScanOutcome("ABC123", "ABORTED", EVENTS[:2], timed_out=True))
    client.fetch_errors.return_value = []
    result = enrichment.process_message(message())
    assert "partial" in result.lower()
    assert any("scan incomplete: stopped after 900 s" in t for t in note_texts(helper))


def test_a_finished_scan_has_no_incomplete_line(helper):
    enrichment, _ = make(helper)
    enrichment.process_message(message())
    assert not any("scan incomplete" in t or "not FINISHED" in t for t in note_texts(helper))


# --- what OpenCTI already knows ---


def make_with_knowledge(helper, lookup):
    client = MagicMock()
    client.run_scan.return_value = ScanOutcome("ABC123", "FINISHED", EVENTS)
    client.fetch_errors.return_value = []
    return SpiderFootEnrichment(helper, SETTINGS, client, knowledge_lookup=lookup), client


def knowledge_notes(helper):
    return [
        o
        for o in sent_bundle(helper)["objects"]
        if o["type"] == "note" and o.get("abstract", "").startswith("OpenCTI knowledge")
    ]


def test_known_observables_are_reported_in_their_own_note(helper):
    from spiderfoot_connector.knowledge import Known

    asked = []

    def lookup(values):
        asked.append(sorted(values))
        return [Known("198.51.100.7", "IPv4-Addr", indicators=[("C2 server", 80)])]

    enrichment, _ = make_with_knowledge(helper, lookup)
    enrichment.process_message(message("example.com"))
    assert len(asked) == 1 and "example.com" in asked[0] and "198.51.100.7" in asked[0]
    (note,) = knowledge_notes(helper)
    assert note["abstract"].startswith("OpenCTI knowledge before this import: 1 of ")
    assert "198.51.100.7 (IPv4-Addr): 1 indicator (highest score 80)" in note["content"]


def test_nothing_known_is_still_stated(helper):
    enrichment, _ = make_with_knowledge(helper, lambda values: [])
    enrichment.process_message(message("example.com"))
    (note,) = knowledge_notes(helper)
    assert "none of the" in note["content"] and "other sources" in note["content"]


def test_a_failing_lookup_never_fails_the_enrichment(helper):
    def lookup(values):
        raise RuntimeError("platform unreachable")

    enrichment, _ = make_with_knowledge(helper, lookup)
    enrichment.process_message(message("example.com"))
    helper.send_stix2_bundle.assert_called_once()
    assert knowledge_notes(helper) == []


def test_no_lookup_configured_means_no_knowledge_note(helper):
    enrichment, _ = make(helper)
    enrichment.process_message(message())
    assert knowledge_notes(helper) == []


def test_knowledge_note_is_attached_to_the_root_target(helper):
    import stix2

    enrichment, _ = make_with_knowledge(helper, lambda values: [])
    enrichment.process_message(message("example.com"))
    (note,) = knowledge_notes(helper)
    assert note["object_refs"] == [stix2.DomainName(value="example.com").id]


# --- changes since the previous scan ---


def make_with_snapshots(helper, lookup, outcome=None):
    client = MagicMock()
    client.run_scan.return_value = outcome or ScanOutcome("ABC123", "FINISHED", EVENTS)
    client.fetch_errors.return_value = []
    return SpiderFootEnrichment(helper, SETTINGS, client, snapshot_lookup=lookup), client


def snapshot_notes(helper):
    return [
        o
        for o in sent_bundle(helper)["objects"]
        if o["type"] == "note" and o.get("abstract", "").startswith("octifoot snapshot for")
    ]


def test_first_enrichment_writes_a_snapshot_note_with_nothing_to_compare(helper):
    enrichment, _ = make_with_snapshots(helper, lambda target: None)
    enrichment.process_message(message("example.com"))
    (note,) = snapshot_notes(helper)
    assert note["abstract"] == "octifoot snapshot for example.com: first snapshot"
    assert "First octifoot snapshot of example.com" in note["content"]
    assert "Snapshot (machine-readable" in note["content"]


def test_a_previous_snapshot_is_compared(helper):
    from spiderfoot_connector.changes import Snapshot

    previous = Snapshot(
        scan="OLD", at="2026-10-01T00:00:00Z", complete=True, hosts=["gone.example.com"]
    )
    asked = []

    def lookup(target):
        asked.append(target)
        return previous

    enrichment, _ = make_with_snapshots(helper, lookup)
    enrichment.process_message(message("example.com"))
    assert asked == ["example.com"]
    (note,) = snapshot_notes(helper)
    assert note["abstract"].startswith("octifoot snapshot for example.com: ")
    assert (
        "Changes since the previous octifoot scan of example.com (2026-10-01, scan OLD)"
        in note["content"]
    )
    assert "hostnames not seen this time: gone.example.com" in note["content"]


def test_an_incomplete_scan_does_not_claim_disappearances(helper):
    from spiderfoot_connector.changes import Snapshot

    previous = Snapshot(
        scan="OLD", at="2026-10-01T00:00:00Z", complete=True, hosts=["gone.example.com"]
    )
    enrichment, _ = make_with_snapshots(
        helper, lambda t: previous, ScanOutcome("ABC123", "ABORTED", EVENTS, timed_out=True)
    )
    enrichment.process_message(message("example.com"))
    (note,) = snapshot_notes(helper)
    assert (
        "not seen this time" not in note["content"]
        and "disappearances are not reported" in note["content"]
    )


def test_unreadable_previous_snapshot_is_stated_and_the_new_one_is_still_written(helper):
    def lookup(target):
        raise RuntimeError("platform unreachable")

    enrichment, _ = make_with_snapshots(helper, lookup)
    enrichment.process_message(message("example.com"))
    helper.send_stix2_bundle.assert_called_once()
    (note,) = snapshot_notes(helper)
    assert "the previous snapshot could not be read" in note["content"]
    assert "Snapshot (machine-readable" in note["content"]


def test_no_snapshot_lookup_configured_means_no_snapshot_note(helper):
    enrichment, _ = make(helper)
    enrichment.process_message(message())
    assert snapshot_notes(helper) == []


def test_the_snapshot_note_is_attached_to_the_root_target(helper):
    import stix2

    enrichment, _ = make_with_snapshots(helper, lambda t: None)
    enrichment.process_message(message("example.com"))
    (note,) = snapshot_notes(helper)
    assert note["object_refs"] == [stix2.DomainName(value="example.com").id]


# --- link to the full SpiderFoot scan ---


def test_ui_url_from_settings_reaches_references_and_the_note(helper):
    linked = load_settings(
        {
            "SPIDERFOOT_URL": "http://sf:5001",
            "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
            "SPIDERFOOT_PROFILE": "full",
            "SPIDERFOOT_UI_URL": "http://localhost:5001",
        }
    )
    client = MagicMock()
    client.run_scan.return_value = ScanOutcome("ABC123", "FINISHED", EVENTS)
    client.fetch_errors.return_value = []
    SpiderFootEnrichment(helper, linked, client).process_message(message("example.com"))
    url = "http://localhost:5001/scaninfo?id=ABC123"
    objects = sent_bundle(helper)["objects"]
    urls = {
        r["url"]
        for o in objects
        for r in o.get("x_opencti_external_references", [])
        if r.get("external_id") == "ABC123"
    }
    assert urls == {url}
    assert any(
        o["type"] == "note" and f"Full results in SpiderFoot: {url}" in o["content"]
        for o in objects
    )


def test_without_ui_url_the_connector_adds_no_links(helper):
    enrichment, _ = make(helper)
    enrichment.process_message(message())
    assert "Full results in SpiderFoot" not in " ".join(note_texts(helper))


# --- free API keys for keyed modules ---

SECRET_KEY = "SENTINEL-KEY-VALUE-123"


def lean_settings():
    return load_settings(
        {
            "SPIDERFOOT_URL": "http://sf:5001",
            "SPIDERFOOT_ALLOWED_DOMAINS": "example.com",
            "SPIDERFOOT_PROFILE": "lean",
        }
    )


def a_keyed_module():
    from spiderfoot_connector.profiles import DENY, lean_modules, load_snapshot

    snapshot, lean = load_snapshot(), set(lean_modules())
    return min(
        n
        for n, m in snapshot.items()
        if "apikey" in m["flags"]
        and "Passive" in m["useCases"]
        and not {"invasive", "tool"} & set(m["flags"])
        and n not in DENY
        and n not in lean
    )


def keyed_enrichment(helper, ring, *, api_works=True):
    from spiderfoot_connector.apikeys import apply_keys  # noqa: F401  (import check)

    client = MagicMock()
    client.run_scan.return_value = ScanOutcome("ABC123", "FINISHED", EVENTS)
    client.fetch_errors.return_value = []
    data = {f"module.{name.split(':')[0]}.{name.split(':')[1]}": "" for name in ring.entries}
    calls = []

    def get_options():
        calls.append("get")
        if not api_works:
            raise RuntimeError("settings API down")
        return "tok", dict(data)

    def save_options(options, token):
        calls.append("save")
        for name, value in options.items():
            module, _, option = name.partition(":")
            data[f"module.{module}.{option}"] = value

    client.get_options.side_effect = get_options
    client.save_options.side_effect = save_options
    return SpiderFootEnrichment(helper, lean_settings(), client, key_ring=ring), client, calls


def test_a_keyed_module_joins_the_scan_only_after_its_key_was_applied(helper):
    from spiderfoot_connector.apikeys import KeyRing

    module = a_keyed_module()
    enrichment, client, calls = keyed_enrichment(helper, KeyRing({f"{module}:api_key": SECRET_KEY}))
    enrichment.process_message(message("example.com"))
    sent = client.run_scan.call_args.kwargs["modules"]
    assert module in sent
    assert calls.index("save") < len(calls)  # the key was written before the scan call


def test_without_a_key_ring_nothing_touches_the_settings_api(helper):
    enrichment, client = make(helper)
    enrichment.process_message(message())
    client.get_options.assert_not_called()
    client.save_options.assert_not_called()


def test_a_failing_settings_api_runs_the_scan_without_the_keyed_module(helper):
    from spiderfoot_connector.apikeys import KeyRing
    from spiderfoot_connector.profiles import lean_modules

    module = a_keyed_module()
    enrichment, client, _ = keyed_enrichment(
        helper, KeyRing({f"{module}:api_key": SECRET_KEY}), api_works=False
    )
    enrichment.process_message(message("example.com"))
    assert client.run_scan.call_args.kwargs["modules"] == lean_modules()
    helper.send_stix2_bundle.assert_called_once()


def test_the_key_value_never_reaches_notes_logs_or_the_work_message(helper):
    from spiderfoot_connector.apikeys import KeyRing

    module = a_keyed_module()
    enrichment, _, _ = keyed_enrichment(helper, KeyRing({f"{module}:api_key": SECRET_KEY}))
    result = enrichment.process_message(message("example.com"))
    assert SECRET_KEY not in result
    assert SECRET_KEY not in str(sent_bundle(helper))
    assert SECRET_KEY not in str(helper.connector_logger.mock_calls)


def test_a_key_that_could_not_be_stored_is_named_in_the_log_but_not_its_value(helper):
    from spiderfoot_connector.apikeys import KeyRing

    enrichment, _, _ = keyed_enrichment(helper, KeyRing({"sfp_not_there:api_key": SECRET_KEY}))
    enrichment._client.get_options.side_effect = lambda: ("tok", {})  # the option does not exist
    enrichment.process_message(message("example.com"))
    logged = str(helper.connector_logger.mock_calls)
    assert "sfp_not_there:api_key" in logged and SECRET_KEY not in logged


# --- configuration errors must be readable and happen before the connector registers ---


def test_a_bad_key_file_stops_main_with_a_readable_message_before_registering(
    monkeypatch, tmp_path, capsys
):
    from spiderfoot_connector import connector

    bad = tmp_path / "keys.json"
    bad.write_text('{"sfp_nope": "' + SECRET_KEY + '"}')
    monkeypatch.setenv("SPIDERFOOT_URL", "http://sf:5001")
    monkeypatch.setenv("SPIDERFOOT_ALLOWED_DOMAINS", "example.com")
    monkeypatch.setenv("SPIDERFOOT_API_KEYS_FILE", str(bad))

    def must_not_register(*args, **kwargs):
        raise AssertionError("the connector registered despite an invalid configuration")

    monkeypatch.setattr(connector, "OpenCTIConnectorHelper", must_not_register)
    with pytest.raises(SystemExit) as exit_info:
        connector.main()
    assert exit_info.value.code == 2
    err = capsys.readouterr().err
    assert "configuration error" in err and "SPIDERFOOT_API_KEYS_FILE" in err and "sfp_nope" in err
    assert SECRET_KEY not in err


def test_a_missing_allowlist_also_stops_main_readably(monkeypatch, capsys):
    from spiderfoot_connector import connector

    monkeypatch.delenv("SPIDERFOOT_ALLOWED_DOMAINS", raising=False)
    monkeypatch.setenv("SPIDERFOOT_URL", "http://sf:5001")
    monkeypatch.setattr(
        connector, "OpenCTIConnectorHelper", lambda *a, **k: (_ for _ in ()).throw(AssertionError())
    )
    with pytest.raises(SystemExit) as exit_info:
        connector.main()
    assert exit_info.value.code == 2 and "SPIDERFOOT_ALLOWED_DOMAINS" in capsys.readouterr().err
