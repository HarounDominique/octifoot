import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from spiderfoot_connector.mapper import map_events

FIXTURE = Path(__file__).parent.parent / "fixtures" / "scan_events.json"
NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)


@pytest.fixture
def events():
    return json.loads(FIXTURE.read_text())


@pytest.fixture
def result(events):
    return map_events(events, target="example.com", scan_id="ABC123", score=30, now=NOW)


def by_type(result, type_):
    return [o for o in result.objects if o.type == type_]


def values(result, type_):
    return sorted(o.value for o in by_type(result, type_))


def test_domains_mapped_deduped_and_lowercased(result):
    # target + www (deduped across two modules); the affiliate name and the false positive are not imported
    assert values(result, "domain-name") == ["example.com", "www.example.com"]


def test_ips_mapped_invalid_skipped(result):
    assert values(result, "ipv4-addr") == ["198.51.100.7", "93.184.216.34"] or values(
        result, "ipv4-addr"
    ) == sorted(["198.51.100.7", "93.184.216.34"])
    assert result.invalid == 1


def test_email_lowercased(result):
    assert values(result, "email-addr") == ["admin@example.com"]


def test_unmapped_types_counted_not_emitted(result):
    assert result.unmapped == {
        "TCP_PORT_OPEN": 1,
        "WEBSERVER_BANNER": 1,
        "AFFILIATE_INTERNET_NAME": 1,
    }
    assert result.false_positives == 1


def test_ip_resolves_from_its_source_host(result):
    domains = {o.value: o.id for o in by_type(result, "domain-name")}
    ips = {o.value: o.id for o in by_type(result, "ipv4-addr")}
    rels = {
        (r.source_ref, r.target_ref): r.relationship_type for r in by_type(result, "relationship")
    }
    assert rels[(domains["www.example.com"], ips["93.184.216.34"])] == "resolves-to"
    # IP whose source was the target itself resolves from the target
    assert rels[(domains["example.com"], ips["198.51.100.7"])] == "resolves-to"


def test_subdomain_and_email_related_to_target(result):
    domains = {o.value: o.id for o in by_type(result, "domain-name")}
    emails = {o.value: o.id for o in by_type(result, "email-addr")}
    rels = {
        (r.source_ref, r.target_ref): r.relationship_type for r in by_type(result, "relationship")
    }
    target = domains["example.com"]
    assert rels[(domains["www.example.com"], target)] == "related-to"
    assert rels[(emails["admin@example.com"], target)] == "related-to"


def test_provenance_on_every_observable(result):
    identity = by_type(result, "identity")[0]
    assert identity.name == "SpiderFoot"
    for o in result.objects:
        if o.type in ("domain-name", "ipv4-addr", "email-addr") and o.value != "example.com":
            assert o.x_opencti_created_by_ref == identity.id
            refs = o.x_opencti_external_references
            assert refs[0]["source_name"] == "SpiderFoot"
            assert refs[0]["external_id"] == "ABC123"
            assert "sfp_" in refs[0]["description"]


def test_imported_domain_gets_the_configured_score(result):
    scores = {
        o.value: o.x_opencti_score
        for o in by_type(result, "domain-name")
        if o.value != "example.com"
    }
    assert scores == {"www.example.com": 30}


def test_summary_note_references_target(result):
    note = by_type(result, "note")[0]
    domains = {o.value: o.id for o in by_type(result, "domain-name")}
    assert note.object_refs == [domains["example.com"]]
    assert "ABC123" in note.content
    assert "TCP_PORT_OPEN" in note.content


def test_deterministic(events):
    a = map_events(events, target="example.com", scan_id="ABC123", score=30, now=NOW)
    b = map_events(events, target="example.com", scan_id="ABC123", score=30, now=NOW)
    assert [o.id for o in a.objects] == [o.id for o in b.objects]


def test_empty_events_still_yields_note_and_target():
    r = map_events([], target="example.com", scan_id="X", score=30, now=NOW)
    assert values(r, "domain-name") == ["example.com"]
    assert len(by_type(r, "note")) == 1
