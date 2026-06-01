# Memory Hub

SQLite-first central memory hub for Hermes, Codex, Claude Code, OpenCode, and other agents.

## MVP features

- SQLite storage with WAL mode
- Typed memories: `fact`, `task`, `decision`, `note`, `project`, `credential_ref`, `session_summary`
- FTS5 search
- Context pack generation
- HTTP API with bearer token auth
- CLI client/local mode

## Quickstart

```bash
uv sync
uv run memhub init --db ./data/memoryhub.sqlite
uv run memhub add "Discord bot token is configured in ~/.hermes/.env" --project hermes --type fact --tags discord,gateway
uv run memhub search discord --project hermes
uv run memhub context --project hermes --goal "debug discord gateway"
```

## Run API

```bash
export MEMORY_HUB_DB=./data/memoryhub.sqlite
export MEMORY_HUB_TOKEN=change-me
uv run uvicorn memory_hub.api:app --host 127.0.0.1 --port 8787
```

Then:

```bash
TOKEN="change-me"
curl -H "Authorization: Bearer ${TOKEN}" http://127.0.0.1:8787/health
```
