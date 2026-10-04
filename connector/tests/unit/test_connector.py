import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from spiderfoot_connector.client import ScanOutcome, SpiderFootError
from spiderfoot_connector.config import load_settings
from spiderfoot_connector.connector import SpiderFootEnrichment, TargetNotAllowed

EVENTS = json.loads((Path(__file__).parent.parent / "fixtures" / "scan_events.json").read_text())
SETTINGS = load_settings(
    {"SPIDERFOOT_URL": "http://sf:5001", "SPIDERFOOT_ALLOWED_DOMAINS": "example.com"}
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
