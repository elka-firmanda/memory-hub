# Memory Hub

SQLite-first central memory hub for Hermes, Codex, Claude Code, OpenCode, and other agents.

## MVP features

- SQLite storage with WAL mode
- Typed memories: `fact`, `task`, `decision`, `note`, `project`, `credential_ref`, `session_summary`
- FTS5 search
- Context pack generation
- HTTP API with bearer token auth
- CLI client/local mode
- Docker image published to GitHub Container Registry

## Docker install

Create a folder on your server:

```bash
mkdir -p ~/memory-hub && cd ~/memory-hub
curl -fsSLO https://raw.githubusercontent.com/elka-firmanda/memory-hub/main/docker-compose.yml
cp .env.example .env 2>/dev/null || true
printf 'MEMORY_HUB_TOKEN=%s\n' "$(openssl rand -hex 32)" > .env
docker compose up -d
```

Health check:

```bash
curl -H 'Authorization: Bearer <your-token>' http://127.0.0.1:8787/health
```

The default compose file binds to `127.0.0.1:8787`, safe for Cloudflare Tunnel or reverse proxy usage.

## Local development quickstart

```bash
uv sync
uv run memhub init --db ./data/memoryhub.sqlite
uv run memhub add "Discord bot token is configured in ~/.hermes/.env" --project hermes --type fact --tags discord,gateway
uv run memhub search discord --project hermes
uv run memhub context --project hermes --goal "debug discord gateway"
```

## Run API without Docker

```bash
export MEMORY_HUB_DB=./data/memoryhub.sqlite
export MEMORY_HUB_TOKEN=change-me
uv run uvicorn memory_hub.api:app --host 127.0.0.1 --port 8787
```

Then:

```bash
curl -H 'Authorization: Bearer <your-token>' http://127.0.0.1:8787/health
```
