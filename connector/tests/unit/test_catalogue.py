import json
from pathlib import Path

from spiderfoot_connector.catalogue import (
    ALLOWED_STATUSES,
    build_catalogue,
    classify_needs,
    load_catalogue,
    render_markdown,
)
from spiderfoot_connector.mapper import IMPORTED_EVENTS
from spiderfoot_connector.profiles import lean_modules, load_snapshot

DATA = Path(__file__).parents[2] / "src/spiderfoot_connector/data"
ROOT = Path(__file__).parents[3]


def types():
    return json.loads((DATA / "sf_event_types_v4.0.json").read_text())


def observed():
    return json.loads((DATA / "observed_events.json").read_text())


def entries():
    return {e["id"]: e for e in load_catalogue()}


# --- classification of what a type needs in order to be produced ---


def mod(produced, *, passive=True, flags=()):
    return {
        "useCases": ["Passive"] if passive else ["Footprint"],
        "flags": list(flags),
        "produced": produced,
        "watched": ["*"],
    }


def test_needs_passive_when_a_lean_module_produces_it():
    meta = {"sfp_a": mod(["X"])}
    assert classify_needs("X", meta, lean={"sfp_a"}) == "passive"


def test_needs_denied_when_only_a_passive_keyless_module_outside_lean_produces_it():
    meta = {"sfp_a": mod(["X"])}
    assert classify_needs("X", meta, lean=set()) == "denied-module"


def test_needs_api_key_when_only_keyed_passive_modules_produce_it():
    meta = {"sfp_a": mod(["X"], flags=["apikey"])}
    assert classify_needs("X", meta, lean=set()) == "api-key"


def test_needs_active_when_only_non_passive_or_invasive_modules_produce_it():
    assert classify_needs("X", {"sfp_a": mod(["X"], passive=False)}, lean=set()) == "active"
    assert classify_needs("X", {"sfp_a": mod(["X"], flags=["invasive"])}, lean=set()) == "active"


def test_needs_none_when_no_module_produces_it():
    assert classify_needs("X", {"sfp_a": mod(["Y"])}, lean={"sfp_a"}) == "none"


def test_a_lean_producer_wins_over_keyed_ones():
    meta = {"sfp_a": mod(["X"]), "sfp_b": mod(["X"], flags=["apikey"])}
    assert classify_needs("X", meta, lean={"sfp_a"}) == "passive"


# --- the committed catalogue ---


def test_every_spiderfoot_event_type_has_exactly_one_entry():
    loaded = load_catalogue()
    assert len(loaded) == len(types()) == 172
    assert {e["id"] for e in loaded} == set(types())


def test_every_entry_is_decided_and_explained():
    for e in entries().values():
        assert e["status"] in ALLOWED_STATUSES, e["id"]
        assert e["action"], e["id"]
        assert len(e["rationale"]) >= 10, e["id"]


def test_imported_status_matches_the_mapper_exactly():
    marked = {i for i, e in entries().items() if e["status"] == "imported"}
    assert marked == IMPORTED_EVENTS


def test_nothing_observed_in_real_scans_is_left_undecided():
    seen = observed()["types"]
    for tid, e in entries().items():
        if tid in seen:
            assert e["status"] in {"imported", "planned", "declined"}, tid
            assert e["observed_events"] == seen[tid]["events"], tid


def test_unobserved_types_are_imported_blocked_no_data_or_declined_by_policy():
    # imported but unobserved means the mapper is only proven on fixtures (e.g. EMAILADDR)
    seen = observed()["types"]
    for tid, e in entries().items():
        if tid not in seen:
            assert e["status"] in {"imported", "blocked", "no-data", "declined"}, tid


def test_imported_types_never_seen_in_real_scans_are_visible_in_the_catalogue():
    unseen = sorted(
        i for i, e in entries().items() if e["status"] == "imported" and not e["observed_events"]
    )
    assert unseen == ["EMAILADDR"]


def test_third_party_families_are_declined_by_policy():
    for tid, e in entries().items():
        if tid.startswith(("AFFILIATE_", "CO_HOSTED_", "BLACKLISTED_")):
            assert e["status"] == "declined", tid


def test_planned_entries_name_the_slice_that_will_do_them():
    planned = [e for e in entries().values() if e["status"] == "planned"]
    assert planned
    for e in planned:
        assert e["slice"], e["id"]


def test_blocked_entries_say_what_unblocks_them():
    for e in entries().values():
        if e["status"] == "blocked":
            assert e["needs"] in {"api-key", "active"}, e["id"]


def test_sensitive_attribution_cases_found_in_real_data_stay_declined():
    # registry/registrar details found in WHOIS text are not the target's own
    for tid in ("COMPANY_NAME", "PHYSICAL_ADDRESS", "LEI", "PHONE_NUMBER"):
        assert entries()[tid]["status"] == "declined", tid


def test_committed_catalogue_is_what_the_generator_produces():
    built = build_catalogue(
        types(), load_snapshot(), set(lean_modules()), observed()["types"], IMPORTED_EVENTS
    )
    assert built == load_catalogue()


def test_markdown_document_is_up_to_date_and_lists_every_type():
    doc = (ROOT / "docs/event-catalogue.md").read_text()
    assert doc == render_markdown(load_catalogue(), observed())
    for tid in types():
        assert f"`{tid}`" in doc or tid in doc, tid
