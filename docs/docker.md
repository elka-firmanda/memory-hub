# Docker deployment

## One-command-ish install

```bash
mkdir -p ~/memory-hub && cd ~/memory-hub
curl -fsSLO https://raw.githubusercontent.com/elka-firmanda/memory-hub/main/docker-compose.yml
printf 'MEMORY_HUB_TOKEN=%s\n' "$(openssl rand -hex 32)" > .env
docker compose up -d
```

## Verify

```bash
curl -H 'Authorization: Bearer <your-token>' http://127.0.0.1:8787/health
```

## Image

GitHub Actions publishes this image on pushes to `main`:

```text
ghcr.io/elka-firmanda/memory-hub:latest
```

## Data

The compose file stores SQLite data in the named volume `memory_hub_data` at `/data/memoryhub.sqlite` inside the container.

## Cloudflare Tunnel

Keep the container bound to localhost and point Cloudflare Tunnel to it:

```yaml
ingress:
  - hostname: memory.example.com
    service: http://127.0.0.1:8787
  - service: http_status:404
```

Put Cloudflare Access in front of the hostname and keep `MEMORY_HUB_TOKEN` enabled.
