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
