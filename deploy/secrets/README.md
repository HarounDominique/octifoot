# Secrets

Put `api-keys.json` here to give octifoot your own free API keys (see `docs/api-keys.md`). Start from `api-keys.example.json`.

This directory is mounted read-only into the connector at `/run/octifoot-secrets`. Everything here except this README, the example and `.gitignore` is ignored by git on purpose: never commit a key.
