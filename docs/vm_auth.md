# Auth and users (VM / self-hosted)

See [security_brief.md](security_brief.md) for HTTPS, firewall, CORS, and production checklist.

Decime uses **JWT authentication** and **PostgreSQL** (`app_users` table) when `DATABASE_URL` is set. For local dev without Postgres, SQLite in `data/decime.db` still works.



## Modes



| Config | Behavior |

|--------|----------|

| No `DATABASE_URL`, `AUTH_ENABLED=false` | Local dev: open API, in-memory training/history |

| No `DATABASE_URL`, `AUTH_ENABLED=true` | SQLite users, in-memory data (single-user dev) |

| `DATABASE_URL` set | **Postgres persistence** — `AUTH_ENABLED=true` **required** |



Public endpoints: `GET /health`, `GET /api/v1/auth/config`, `POST /api/v1/auth/login`, `POST /api/v1/auth/register` (if allowed).



## Environment (`.env`)



```env

APP_ENV=production

DATABASE_URL=postgresql://decime:decime@postgres:5432/decime

AUTH_ENABLED=true

AUTH_JWT_SECRET=<long-random-secret-min-32-chars>

AUTH_ALLOW_REGISTRATION=false

AUTH_BOOTSTRAP_ADMIN_EMAIL=admin@example.com

AUTH_BOOTSTRAP_ADMIN_PASSWORD=<strong-password>

```



Migrations run automatically on API startup from `supabase/migrations/`.



## Create admin manually



```bash

cd apps/api

.venv\Scripts\activate

py ../../scripts/create_admin.py --email admin@example.com --password "YourStrongPass"

```



Works with SQLite (no `DATABASE_URL`) or Postgres.



## Per-user data



When Postgres is enabled, all training, history, audio paths, and extractions are scoped by `user_id`. Beta users on one VM do not share data.



Default training list «My phrases» is created on user registration.



## API



| Method | Path | Who |

|--------|------|-----|

| GET | `/api/v1/auth/config` | anyone |

| POST | `/api/v1/auth/login` | anyone |

| POST | `/api/v1/auth/register` | anyone if `AUTH_ALLOW_REGISTRATION=true` |

| GET | `/api/v1/auth/me` | logged-in user |

| GET | `/api/v1/auth/users` | admin |

| POST | `/api/v1/auth/users` | admin |

| PATCH | `/api/v1/auth/users/{id}` | admin |



Use header: `Authorization: Bearer <access_token>` (web app and Android native HTTP).



## VM checklist

1. Complete [security_brief.md](security_brief.md) P0 items (HTTPS, firewall, auth).
2. Deploy with [deploy/README.md](../deploy/README.md) (Caddy + Docker Compose).
3. Set `DATABASE_URL`, `AUTH_ENABLED=true`, `AUTH_JWT_SECRET` ≥ 32 chars.
4. Create admin (bootstrap or `create_admin.py`).
5. `AUTH_ALLOW_REGISTRATION=false` — users via admin only.
6. Back up Postgres + audio: [deploy/scripts/backup.sh](../deploy/scripts/backup.sh).



## Analytics



API writes to `event_log` in Postgres. n8n workflows: [n8n_workflows.md](n8n_workflows.md).

