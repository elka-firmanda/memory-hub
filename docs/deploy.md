# Memory Hub MVP deployment

## Systemd service

```ini
[Unit]
Description=Memory Hub API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/memory-hub
Environment=MEMORY_HUB_DB=/var/lib/memory-hub/memoryhub.sqlite
Environment=MEMORY_HUB_TOKEN=change-me-long-random-token
ExecStart=/usr/bin/env uv run uvicorn memory_hub.api:app --host 127.0.0.1 --port 8787
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Cloudflare Tunnel

Expose only the localhost API:

```yaml
tunnel: memory-hub
ingress:
  - hostname: memory.example.com
    service: http://127.0.0.1:8787
  - service: http_status:404
```

Put Cloudflare Access in front of `memory.example.com`, then still keep `MEMORY_HUB_TOKEN` enabled.

## Agent env

```bash
export MEMORY_HUB_URL=https://memory.example.com
export MEMORY_HUB_TOKEN=change-me-long-random-token
```

## Backup

```bash
sqlite3 /var/lib/memory-hub/memoryhub.sqlite ".backup '/var/backups/memory-hub/memoryhub-$(date +%F).sqlite'"
```
