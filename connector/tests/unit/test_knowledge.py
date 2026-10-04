from spiderfoot_connector.knowledge import Known, query_known, render_knowledge


def node(
    value,
    etype="IPv4-Addr",
    indicators=(),
    reports=(),
    labels=(),
    creator=None,
):
    return {
        "entity_type": etype,
        "observable_value": value,
        "createdBy": {"name": creator} if creator else None,
        "objectLabel": [{"value": label} for label in labels],
        "indicators": {
            "edges": [
                {"node": {"name": n, "x_opencti_score": s, "revoked": r}} for n, s, r in indicators
            ]
        },
        "reports": {"edges": [{"node": {"name": n}} for n in reports]},
    }


def fake_query(nodes, calls=None):
    def run(query, variables):
        if calls is not None:
            calls.append(variables["values"])
        wanted = set(variables["values"])
        return {
            "data": {
                "stixCyberObservables": {
                    "edges": [{"node": n} for n in nodes if n["observable_value"] in wanted]
                }
            }
        }

    return run


# --- what counts as knowledge ---


def test_indicator_report_label_and_other_creator_each_count():
    nodes = [
        node("203.0.113.1", indicators=[("C2 server", 80, False)]),
        node("203.0.113.2", reports=["Campaign X"]),
        node("203.0.113.3", labels=["tlp:amber"]),
        node("203.0.113.4", creator="Feed Connector"),
    ]
    known = query_known(fake_query(nodes), [n["observable_value"] for n in nodes])
    assert [k.value for k in known] == ["203.0.113.1", "203.0.113.2", "203.0.113.3", "203.0.113.4"]
    assert known[0].indicators == [("C2 server", 80)]
    assert known[1].reports == ["Campaign X"]
    assert known[2].labels == ["tlp:amber"]
    assert known[3].creators == ["Feed Connector"]


def test_octifootss_own_objects_never_count():
    nodes = [
        node("203.0.113.9", creator="SpiderFoot", labels=["spiderfoot:malicious"]),
        node("203.0.113.8", creator="SpiderFoot"),
    ]
    assert query_known(fake_query(nodes), ["203.0.113.9", "203.0.113.8"]) == []


def test_other_labels_count_even_next_to_ours():
    nodes = [node("203.0.113.9", creator="SpiderFoot", labels=["spiderfoot:malicious", "apt"])]
    (k,) = query_known(fake_query(nodes), ["203.0.113.9"])
    assert k.labels == ["apt"] and k.creators == []


def test_an_observable_with_nothing_attached_is_not_known():
    assert query_known(fake_query([node("example.com", "Domain-Name")]), ["example.com"]) == []


def test_revoked_indicators_do_not_count():
    nodes = [node("203.0.113.1", indicators=[("old", 90, True)])]
    assert query_known(fake_query(nodes), ["203.0.113.1"]) == []


def test_values_unknown_to_the_platform_are_simply_absent():
    assert query_known(fake_query([]), ["198.51.100.1"]) == []


# --- batching and robustness ---


def test_values_are_deduplicated_and_batched_by_fifty():
    calls = []
    values = [f"192.0.2.{i}" for i in range(1, 121)] + ["192.0.2.1"]
    query_known(fake_query([], calls), values)
    assert [len(c) for c in calls] == [50, 50, 20]
    assert len({v for c in calls for v in c}) == 120


def test_no_values_means_no_query():
    calls = []
    assert query_known(fake_query([], calls), []) == []
    assert calls == []


def test_the_query_only_reads():
    seen = []

    def run(query, variables):
        seen.append(query)
        return {"data": {"stixCyberObservables": {"edges": []}}}

    query_known(run, ["203.0.113.1"])
    assert seen and all("mutation" not in q for q in seen)


# --- rendering ---


def test_text_for_known_observables_has_counts_names_labels_and_creator():
    known = [
        Known(
            "203.0.113.1",
            "IPv4-Addr",
            indicators=[("C2 server", 80), ("Scanner", 40)],
            reports=["Campaign X", "Report Y"],
            labels=["apt", "tlp:amber"],
            creators=["Feed Connector"],
        )
    ]
    abstract, text = render_knowledge(known, 7)
    assert abstract == "OpenCTI knowledge before this import: 1 of 7 observables already known"
    assert text.splitlines()[0].startswith(
        "OpenCTI knowledge (queried by octifoot before this import"
    )
    line = text.splitlines()[1]
    assert line.startswith("- 203.0.113.1 (IPv4-Addr): 2 indicators (highest score 80)")
    assert "2 reports (Campaign X; Report Y)" in line
    assert "labels: apt, tlp:amber" in line and "also from Feed Connector" in line


def test_none_known_is_stated_explicitly():
    abstract, text = render_knowledge([], 4)
    assert abstract == "OpenCTI knowledge before this import: 0 of 4 observables already known"
    assert "none of the 4 imported observables" in text and "other sources" in text


def test_report_names_are_capped_per_observable_and_lines_overall():
    known = [
        Known(f"192.0.2.{i}", "IPv4-Addr", reports=[f"R{j}" for j in range(8)]) for i in range(25)
    ]
    _, text = render_knowledge(known, 25)
    lines = text.splitlines()[1:]
    assert "R4" in lines[0] and "R5" not in lines[0] and "8 reports" in lines[0]
    assert len([ln for ln in lines if ln.startswith("- 192")]) == 20
    assert lines[-1] == "- and 5 more"


def test_rendering_is_deterministic_regardless_of_order():
    a = Known("203.0.113.2", "IPv4-Addr", labels=["x"])
    b = Known("203.0.113.1", "IPv4-Addr", labels=["y"])
    assert render_knowledge([a, b], 2) == render_knowledge([b, a], 2)
