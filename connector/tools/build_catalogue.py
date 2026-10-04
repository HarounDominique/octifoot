"""Regenerate data/event_catalogue.json and docs/event-catalogue.md from the committed inputs.

python tools/build_catalogue.py
"""

import json
from pathlib import Path

from spiderfoot_connector.catalogue import build_catalogue, render_markdown
from spiderfoot_connector.mapper import IMPORTED_EVENTS
from spiderfoot_connector.profiles import lean_modules, load_snapshot

DATA = Path(__file__).parents[1] / "src/spiderfoot_connector/data"
DOC = Path(__file__).parents[2] / "docs/event-catalogue.md"


def main() -> None:
    types = json.loads((DATA / "sf_event_types_v4.0.json").read_text())
    observed = json.loads((DATA / "observed_events.json").read_text())
    entries = build_catalogue(
        types, load_snapshot(), set(lean_modules()), observed["types"], IMPORTED_EVENTS
    )
    (DATA / "event_catalogue.json").write_text(json.dumps(entries, indent=1) + "\n")
    DOC.write_text(render_markdown(entries, observed))
    print(f"{len(entries)} event types written")


if __name__ == "__main__":
    main()
