from pathlib import Path

ROOT = Path(__file__).parents[3]
SECRETS = ROOT / "deploy" / "secrets"


def test_only_the_readme_the_example_and_the_ignore_file_are_tracked_by_rule():
    rules = (SECRETS / ".gitignore").read_text().splitlines()
    assert "*" in rules  # everything is ignored ...
    assert {"!.gitignore", "!README.md", "!api-keys.example.json"} <= set(
        rules
    )  # ... except these three


def test_the_real_key_file_name_is_not_among_the_exceptions():
    rules = (SECRETS / ".gitignore").read_text().splitlines()
    assert "!api-keys.json" not in rules and "!*.json" not in rules


def test_the_example_holds_only_placeholders_and_is_valid_for_the_loader(tmp_path):
    import json

    from spiderfoot_connector.apikeys import load_keyring
    from spiderfoot_connector.profiles import load_snapshot

    example = SECRETS / "api-keys.example.json"
    data = json.loads(example.read_text())
    assert data and all(v == "PASTE_YOUR_OWN_FREE_KEY_HERE" for v in data.values())
    assert load_keyring(str(example), load_snapshot()).modules == frozenset(data)


def test_compose_mounts_the_secrets_directory_read_only_and_passes_the_setting():
    compose = (ROOT / "deploy" / "docker-compose.yml").read_text()
    assert "./secrets:/run/octifoot-secrets:ro" in compose
    assert "SPIDERFOOT_API_KEYS_FILE=${SPIDERFOOT_API_KEYS_FILE:-}" in compose
