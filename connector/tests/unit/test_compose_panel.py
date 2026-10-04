import re
from pathlib import Path

COMPOSE = (Path(__file__).parents[3] / "deploy" / "docker-compose.yml").read_text()


def connector_block():
    start = COMPOSE.index("  connector-spiderfoot:")
    end = COMPOSE.index("\nvolumes:", start)
    return COMPOSE[start:end]


def ports_section():
    block = connector_block()
    start = block.index("    ports:\n") + len("    ports:\n")
    section = []
    for line in block[start:].splitlines():
        if line.startswith("    ") and not line.startswith("      "):
            break  # next key of the service
        section.append(line)
    return section


def test_the_panel_port_is_published_on_loopback_only():
    items = [ln.strip() for ln in ports_section() if ln.strip().startswith("- ")]
    assert items, "the connector publishes the panel port"
    assert all(item.startswith('- "127.0.0.1:') for item in items), items


def test_the_panel_is_off_unless_a_token_is_set():
    assert "OCTIFOOT_UI_TOKEN=${OCTIFOOT_UI_TOKEN:-}" in connector_block()


def test_the_panel_state_lives_in_a_named_volume():
    assert "octifoot-state:/var/lib/octifoot" in connector_block()
    assert re.search(r"^  octifoot-state:", COMPOSE, re.MULTILINE)


def test_the_example_env_documents_the_token_with_no_default_value():
    example = (Path(__file__).parents[3] / "deploy" / ".env.example").read_text()
    assert re.search(r"^OCTIFOOT_UI_TOKEN=$", example, re.MULTILINE)
