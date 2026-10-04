import json
from pathlib import Path

from spiderfoot_connector.mapper import IMPORTED_EVENTS
from spiderfoot_connector.profiles import DENY, derive_lean, lean_modules, load_snapshot

REQUIRED = {
    "sfp_crt",
    "sfp_dnsraw",
    "sfp_dnsresolve",
    "sfp_maltiverse",
    "sfp_ripe",
    "sfp_voipbl",
}


def mod(watched, produced, uses=("Passive",), flags=()):
    return {
        "useCases": list(uses),
        "flags": list(flags),
        "watched": list(watched),
        "produced": list(produced),
    }


def test_reachable_passive_modules_are_included():
    meta = {
        "a": mod(["DOMAIN_NAME"], ["IP_ADDRESS"]),
        "b": mod(["IP_ADDRESS"], ["BGP_AS_MEMBER"]),
    }
    assert derive_lean(meta, frozenset()) == ["a", "b"]


def test_unreachable_module_excluded():
    meta = {"a": mod(["DOMAIN_NAME"], ["X"]), "c": mod(["NEVER_PRODUCED"], ["Y"])}
    assert derive_lean(meta, frozenset()) == ["a"]


def test_wildcard_watcher_included():
    assert derive_lean({"w": mod(["*"], [])}, frozenset()) == ["w"]


def test_non_passive_apikey_invasive_tool_excluded():
    meta = {
        "ok": mod(["DOMAIN_NAME"], []),
        "active": mod(["DOMAIN_NAME"], [], uses=("Footprint", "Investigate")),
        "key": mod(["DOMAIN_NAME"], [], flags=("apikey",)),
        "inv": mod(["DOMAIN_NAME"], [], flags=("invasive",)),
        "tool": mod(["DOMAIN_NAME"], [], flags=("tool",)),
    }
    assert derive_lean(meta, frozenset()) == ["ok"]


def test_deny_list_removes_module_and_what_only_it_reaches():
    meta = {
        "a": mod(["DOMAIN_NAME"], ["IP_ADDRESS"]),
        "bad": mod(["IP_ADDRESS"], ["CO_HOSTED_SITE"]),
        "downstream": mod(["CO_HOSTED_SITE"], ["Z"]),
    }
    assert derive_lean(meta, frozenset({"bad"})) == ["a"]


def test_output_is_sorted_and_deterministic():
    meta = {n: mod(["DOMAIN_NAME"], []) for n in ("zeta", "alpha", "mid")}
    assert derive_lean(meta, frozenset()) == ["alpha", "mid", "zeta"]


# --- real SpiderFoot v4.0 snapshot ---


def test_real_lean_list_is_safe_and_useful():
    snapshot = load_snapshot()
    lean = lean_modules()
    assert REQUIRED <= set(lean)
    assert DENY.isdisjoint(lean)
    for name in lean:
        meta = snapshot[name]
        assert "Passive" in meta["useCases"], name
        assert not {"apikey", "invasive", "tool"} & set(meta["flags"]), name


def test_real_lean_is_a_strict_subset_of_passive():
    snapshot = load_snapshot()
    passive = {n for n, m in snapshot.items() if "Passive" in m["useCases"]}
    assert set(lean_modules()) < passive


def test_committed_list_matches_derivation():
    committed = json.loads(
        (Path(__file__).parents[2] / "src/spiderfoot_connector/data/lean_modules.json").read_text()
    )
    assert committed == derive_lean(load_snapshot(), DENY)


CLOUD_BUCKET_MODULES = frozenset(
    {"sfp_s3bucket", "sfp_azureblobstorage", "sfp_digitaloceanspace", "sfp_googleobjectstorage"}
)


def test_deny_list_is_the_evidence_based_set():
    # robtex/countryname: co-host chain (fast-scan-profile). Cloud buckets: they guess thousands of
    # bucket names against third-party storage hosts (s3bucket alone kept a scan running 164 s
    # after every other module had finished) and their events are not imported.
    assert DENY == frozenset({"sfp_robtex", "sfp_countryname"}) | CLOUD_BUCKET_MODULES


def test_lean_loses_no_event_type_the_connector_imports():
    snapshot = load_snapshot()
    passive = {n for n, m in snapshot.items() if "Passive" in m["useCases"]}

    def importable(modules):
        return {e for n in modules for e in snapshot[n]["produced"]} & IMPORTED_EVENTS

    assert importable(passive) <= importable(set(lean_modules()))


def test_denied_modules_produce_nothing_the_connector_imports():
    snapshot = load_snapshot()
    for name in CLOUD_BUCKET_MODULES:
        assert not set(snapshot[name]["produced"]) & IMPORTED_EVENTS, name


# --- keyed modules (free API keys provided by the owner) ---


def _keyed(flags, name="sfp_k", watched=("DOMAIN_NAME",)):
    return {
        name: {
            "useCases": ["Passive"],
            "flags": flags,
            "watched": list(watched),
            "produced": ["IP_ADDRESS"],
        }
    }


def test_a_keyed_module_is_left_out_without_its_key_and_in_with_it():
    meta = _keyed(["apikey"])
    assert derive_lean(meta, frozenset()) == []
    assert derive_lean(meta, frozenset(), frozenset({"sfp_k"})) == ["sfp_k"]


def test_a_key_never_turns_an_invasive_or_tool_module_on():
    for flags in (["apikey", "invasive"], ["apikey", "tool"]):
        assert derive_lean(_keyed(flags), frozenset(), frozenset({"sfp_k"})) == []


def test_the_deny_list_still_wins_over_a_key():
    assert derive_lean(_keyed(["apikey"]), frozenset({"sfp_k"}), frozenset({"sfp_k"})) == []


def test_a_key_does_not_make_an_unreachable_module_run():
    meta = _keyed(["apikey"], watched=("SOMETHING_NEVER_PRODUCED",))
    assert derive_lean(meta, frozenset(), frozenset({"sfp_k"})) == []


def test_without_keys_the_committed_list_is_returned_unchanged():
    from spiderfoot_connector.profiles import lean_modules_with

    assert lean_modules_with(frozenset()) == lean_modules()


def test_with_real_keyed_modules_the_list_grows_by_exactly_those_modules():
    from spiderfoot_connector.profiles import lean_modules_with

    snapshot = load_snapshot()
    keyed = sorted(
        n
        for n, m in snapshot.items()
        if "apikey" in m["flags"]
        and "Passive" in m["useCases"]
        and not {"invasive", "tool"} & set(m["flags"])
        and n not in DENY
        and n not in lean_modules()
    )
    assert keyed, "the snapshot should contain keyed passive modules"
    pick = frozenset(keyed[:3])
    grown = lean_modules_with(pick)
    assert set(lean_modules()) <= set(grown)
    assert set(grown) - set(lean_modules()) <= pick
    assert grown == sorted(grown)


def test_unknown_and_active_keyed_names_are_ignored_by_the_real_list():
    from spiderfoot_connector.profiles import lean_modules_with

    snapshot = load_snapshot()
    # in SpiderFoot v4.0 no module is both keyed and active, so this guard is defensive; use one if it ever exists
    active = next(
        (
            n
            for n, m in snapshot.items()
            if "apikey" in m["flags"] and {"invasive", "tool"} & set(m["flags"])
        ),
        None,
    )
    names = frozenset({"sfp_does_not_exist", *([active] if active else [])})
    assert lean_modules_with(names) == lean_modules()
