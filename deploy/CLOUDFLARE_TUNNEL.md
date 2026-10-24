# Cloudflare Tunnel — path B (shared VM)

Use when port **443** is already taken (x-ui/xray). Decime does not bind host ports.

## 1. Add domain to Cloudflare

1. [Cloudflare Dashboard](https://dash.cloudflare.com) → **Add site** → `decime.online`
2. Choose Free plan
3. Replace nameservers at your registrar with Cloudflare NS (wait until Active)

## 2. Create tunnel

1. [Zero Trust](https://one.dash.cloudflare.com) → **Networks** → **Tunnels**
2. **Create a tunnel** → name: `decime`
3. **Install connector** → **Docker** → copy the token (`eyJ...`)

## 3. Public hostnames (in tunnel config)

Add three routes — **Service type: HTTP**, same internal URL for all:

| Public hostname | Service URL |
|-----------------|-------------|
| `decime.online` | `http://caddy:80` |
| `www.decime.online` | `http://caddy:80` |
| `api.decime.online` | `http://caddy:80` |

Caddy routes `api.decime.online` to FastAPI by `Host` header.

> Use `caddy:80`, not `localhost` — `cloudflared` runs in the same Docker network as Caddy.

Cloudflare creates DNS records automatically when you save hostnames.

## 4. VM `.env`

```env
CLOUDFLARE_TUNNEL_TOKEN=eyJh...
```

## 5. Start tunnel connector on VM

```bash
cd ~/decime/deploy
./scripts/bootstrap-vm.sh
# or if stack already running:
docker compose -f docker-compose.yml -f docker-compose.shared-vm.yml \
  -f docker-compose.cloudflare-tunnel.yml --profile tunnel up -d cloudflared
```

## 6. Verify

```bash
curl -s https://api.decime.online/health
```

Browser: `https://decime.online/login/` — admin from `AUTH_BOOTSTRAP_ADMIN_*`.

## Does not affect

- x-ui / xray on `:443`
- bemulator postgres `:5432`, redis `:6379`
