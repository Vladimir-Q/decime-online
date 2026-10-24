# Decime UY --- Security Brief

**Version:** 0.1 **Date:** 2026-06-23

## Goal

Expose Decime UY to the Internet with reasonable security for a
solo-developer MVP.

------------------------------------------------------------------------

## Public endpoints

Public DNS:

-   decime.online
-   www.decime.online
-   api.decime.online

Only ports 80 and 443 should be exposed.

------------------------------------------------------------------------

## Reverse proxy

Use Caddy (preferred) or nginx.

Architecture:

Internet ↓ Caddy ↓ decime.online → Next.js api.decime.online → FastAPI

FastAPI must not be exposed directly on port 8000.

------------------------------------------------------------------------

## Forbidden public services

Do not expose:

-   Ollama (11434)
-   Orpheus (5005)
-   PostgreSQL (5432)
-   n8n (5678)
-   Next.js dev server (3000)

Bind these services to localhost or internal Docker networks.

------------------------------------------------------------------------

## HTTPS

Use Let's Encrypt automatic certificates.

Force HTTPS and redirect HTTP to HTTPS.

------------------------------------------------------------------------

## Authentication

Before public deployment:

AUTH_ENABLED=true

Use a strong AUTH_JWT_SECRET.

Disable open registration by default.

------------------------------------------------------------------------

## CORS

Avoid '\*' in production.

Allow only:

-   https://decime.online
-   https://www.decime.online

------------------------------------------------------------------------

## n8n

n8n should not be publicly accessible without protection.

Recommended:

-   Basic Auth
-   HTTPS
-   strong passwords

------------------------------------------------------------------------

## SSH

Prefer key authentication.

Disable password login if possible.

Restrict access by IP when feasible.

------------------------------------------------------------------------

## Secrets

Keep API keys only in .env.

Never commit secrets to Git.

------------------------------------------------------------------------

## Firewall

Externally exposed:

-   80
-   443

Everything else should remain closed.

------------------------------------------------------------------------

## Backup

Regularly back up:

-   database
-   audio files
-   environment files

------------------------------------------------------------------------

## Priority checklist

P0

-   HTTPS
-   AUTH_ENABLED=true
-   firewall
-   reverse proxy

P1

-   backups
-   CORS
-   SSH hardening

P2

-   monitoring
-   fail2ban
-   audit logs
