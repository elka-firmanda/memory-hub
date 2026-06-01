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
curl http://127.0.0.1:8787/health
```

The default compose file binds to `127.0.0.1:8787`, safe for Cloudflare Tunnel or reverse proxy usage.

## Install as an MCP server in an agent

Memory Hub exposes a **Streamable HTTP MCP endpoint** at:

```text
<MEMORY_HUB_URL>/mcp/
```

If bearer auth is enabled with `MEMORY_HUB_TOKEN`, MCP clients must send:

```text
Authorization header value: Bearer REPLACE_WITH_MEMORY_HUB_TOKEN
```

### Agent instruction

Give this repo to any agent and say:

```text
Check this repository and install Memory Hub as an MCP server.
Use this MCP URL: <YOUR_MEMORY_HUB_MCP_URL>
Use the bearer token from the host's Memory Hub configuration/environment; do not paste or store the raw token in memory.
After installing, verify the MCP tools are available by listing tools or calling memory_list.
```

Replace the URL with your deployment URL if different.

### Hermes Agent

Preferred CLI flow:

```bash
hermes mcp add memoryhub --url <YOUR_MEMORY_HUB_MCP_URL>
hermes mcp test memoryhub
```

If the server has `MEMORY_HUB_TOKEN` enabled, make sure the MCP entry includes the `Authorization` header below.
If your Hermes version expects manual config, add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  memoryhub:
    url: "<YOUR_MEMORY_HUB_MCP_URL>"
    headers:
      Authorization: "Bearer REPLACE_WITH_MEMORY_HUB_TOKEN"
    timeout: 120
    connect_timeout: 60
```

Then restart Hermes or run `/reload-mcp` if available.

### Generic MCP client config

For MCP clients that use JSON config, use this shape:

```json
{
  "mcpServers": {
    "memoryhub": {
      "url": "<YOUR_MEMORY_HUB_MCP_URL>",
      "headers": {
        "Authorization": "Bearer REPLACE_WITH_MEMORY_HUB_TOKEN"
      }
    }
  }
}
```

### Available MCP tools

- `memory_write` — write a typed memory record
- `memory_search` — search central memories with SQLite FTS5
- `memory_list` — list recent memories
- `memory_read` — read one memory by ID
- `memory_update` — update an existing memory
- `memory_context` — generate a compact context pack for a project/goal

Security notes:

- Never store raw API keys, passwords, or bearer tokens inside Memory Hub.
- Store credential references only, for example: `MEMORY_HUB_TOKEN lives in ~/.hermes/.env`.
- `/health` is public for health checks; `/mcp/` and API endpoints require bearer auth when `MEMORY_HUB_TOKEN` is set.
- For non-local MCP domains, set `MEMORY_HUB_MCP_ALLOWED_HOSTS` and `MEMORY_HUB_MCP_ALLOWED_ORIGINS` as comma-separated allowlists, for example `memory.example.com:*` and `https://memory.example.com:*`.

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
curl http://127.0.0.1:8787/health
```
