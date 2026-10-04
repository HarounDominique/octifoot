from datetime import UTC, datetime

from spiderfoot_connector.mapper import map_events

NOW = datetime(2026, 10, 4, 6, 0, 0, tzinfo=UTC)
EVENTS = [
    {
        "event_type": "INTERNET_NAME",
        "data": "www.example.com",
        "source_data": "example.com",
        "module": "sfp_crt",
        "false_positive": 0,
    }
]


def run(source_errors=None):
    kwargs = {} if source_errors is None else {"source_errors": source_errors}
    return map_events(EVENTS, target="example.com", scan_id="S1", score=30, now=NOW, **kwargs)


def note(result):
    (n,) = [o for o in result.objects if o.type == "note"]
    return n.content


def health_line(result):
    lines = [
        ln for ln in note(result).splitlines() if ln.startswith("Sources that reported errors")
    ]
    assert len(lines) == 1
    return lines[0]


def test_no_errors_means_no_line():
    assert "Sources that reported errors" not in note(run([]))


def test_default_call_without_errors_is_unchanged():
    assert note(run()) == note(run([]))


def test_modules_with_most_errors_come_first_then_by_name():
    line = health_line(
        run(
            [
                ("sfp_sublist3r", 'Bad response code "None" from Sublist3r API'),
                ("sfp_commoncrawl", "Unable to fetch CommonCrawl index."),
                ("sfp_sublist3r", "Error querying Sublist3r API"),
            ]
        )
    )
    assert "(2 modules" in line
    assert line.index("sfp_sublist3r") < line.index("sfp_commoncrawl")  # 2 errors before 1
    assert 'sfp_sublist3r: Bad response code "None" from Sublist3r API (2)' in line
    assert "sfp_commoncrawl: Unable to fetch CommonCrawl index. (1)" in line
    assert "Error querying Sublist3r API" not in line  # only the first message


def test_line_states_what_it_cannot_detect():
    line = health_line(run([("sfp_koodous", "Unexpected reply from Koodous: 404")]))
    assert "reports as 'no information'" in line


def test_long_messages_are_cut():
    line = health_line(run([("sfp_x", "e" * 200)]))
    assert "e" * 80 in line and "e" * 81 not in line


def test_more_than_eight_modules_are_capped_with_a_remainder():
    errors = [(f"sfp_m{i:02d}", "boom") for i in range(11)]
    line = health_line(run(errors))
    assert "(11 modules" in line
    assert "sfp_m07" in line and "sfp_m08" not in line
    assert "and 3 more" in line


def test_errors_never_change_the_imported_objects():
    base = {o.id for o in run([]).objects if o.type != "note"}
    with_errors = {o.id for o in run([("sfp_x", "boom")]).objects if o.type != "note"}
    assert base == with_errors


def test_line_is_deterministic_regardless_of_input_order():
    a = [("sfp_b", "two"), ("sfp_a", "one")]
    assert note(run(a)) == note(run(list(reversed(a))))


def test_equal_counts_fall_back_to_alphabetical_order():
    line = health_line(run([("sfp_b", "x"), ("sfp_a", "x")]))
    assert line.index("sfp_a:") < line.index("sfp_b:")
