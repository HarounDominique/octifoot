from spiderfoot_connector.expansion import plan_next

AL = frozenset({"example.com"})


def plan(discovered, scanned=(), budget=10, allowlist=AL):
    return plan_next(discovered, scanned=set(scanned), allowlist=allowlist, remaining_budget=budget)


def test_allowlisted_discoveries_are_targets_in_order():
    p = plan(["b.example.com", "a.example.com"])
    assert p.targets == ["b.example.com", "a.example.com"]
    assert p.out_of_scope == [] and p.budget_skipped == []


def test_out_of_scope_never_a_target():
    p = plan(["a.example.com", "cdn.partner.net", "evilexample.com"])
    assert p.targets == ["a.example.com"]
    assert p.out_of_scope == ["cdn.partner.net", "evilexample.com"]


def test_already_scanned_and_duplicates_are_dropped():
    p = plan(["a.example.com", "A.example.com.", "b.example.com"], scanned={"a.example.com"})
    assert p.targets == ["b.example.com"]
    assert p.out_of_scope == [] and p.budget_skipped == []


def test_budget_caps_targets_and_reports_rest():
    p = plan(["a.example.com", "b.example.com", "c.example.com"], budget=2)
    assert p.targets == ["a.example.com", "b.example.com"]
    assert p.budget_skipped == ["c.example.com"]


def test_zero_budget_scans_nothing():
    p = plan(["a.example.com"], budget=0)
    assert p.targets == []
    assert p.budget_skipped == ["a.example.com"]


def test_empty_allowlist_scopes_everything_out():
    p = plan(["a.example.com"], allowlist=frozenset())
    assert p.targets == [] and p.out_of_scope == ["a.example.com"]


def test_blank_entries_ignored():
    assert plan(["", "  "]).targets == []
