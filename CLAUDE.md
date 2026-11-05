# WHOOP Dashboard — Project Rules & Context

## Security rules (non-negotiable, apply to every session)

- **NEVER commit `.env`** — it contains API keys, tokens, and the database password.
- **NEVER commit `data/`** — CSV files contain personal health data; `profile.json` contains name and email.
- **NEVER commit `Get_crednetilas.py`** — it has hardcoded credentials. It must be deleted before any push.
- **NEVER hardcode secrets in any file** — all credentials go in `.env` only.
- **Before every `git add`**: confirm `.gitignore` is covering `.env`, `data/`, and `Get_crednetilas.py`.
- If a secret is ever accidentally committed: rotate the credential immediately and rewrite git history.

## Project overview
Personal fitness dashboard — fetches data from the WHOOP API and displays it in a Plotly Dash app backed by Neon (PostgreSQL), provisioned through the Vercel Marketplace. (Migrated from Supabase on 2026-11-05.)

## Files
| File | Purpose |
|---|---|
| `auth.py` | One-time OAuth2 flow — run manually to get tokens |
| `fetch.py` | Pulls data from WHOOP API with auto token refresh |
| `store.py` | Saves fetched data to Neon + local CSV backup |
| `main.py` | Daily runner: refresh token → fetch all → save |
| `dashboard.py` | Plotly Dash app, reads from Neon |
| `api/index.py` | Vercel serverless entry point |
| `vercel.json` | Vercel routing config |
| `requirements.txt` | Python dependencies for Vercel |

## Daily workflow
```
python3 main.py        # fetch new WHOOP data → save to Neon
python3 dashboard.py   # view dashboard at http://127.0.0.1:8050
```

## Environment variables (`.env` only — never in code or Git)
- `WHOOP_CLIENT_ID`
- `WHOOP_CLIENT_SECRET`
- `WHOOP_ACCESS_TOKEN`
- `WHOOP_REFRESH_TOKEN`
- `DATABASE_URL` — Neon pooled connection string. Must start with `postgresql+psycopg2://` (plain `postgresql://` makes SQLAlchemy 2.1+ look for `psycopg` v3, which isn't installed)

## WHOOP API
- Base URL: `https://api.prod.whoop.com/developer`
- All endpoints are v2 (e.g. `/v2/activity/sleep`, `/v2/recovery`, `/v2/cycle`)
- Token refresh: `POST https://api.prod.whoop.com/oauth/oauth2/token`
- Scopes: `read:sleep read:recovery read:workout read:profile read:cycles offline`

## Database (Neon)
- Free Neon Postgres via Vercel Marketplace — resource `neon-beige-dog`, connected to Vercel project `whoop-fun-dashboard`
- Tables: `sleep`, `recovery`, `workouts`, `cycles`, `whoop_tokens` (id=1 holds the live WHOOP token pair — source of truth for CI)
- `DATABASE_URL` is set in three places: `.env`, GitHub secret, Vercel env (Production + Preview)
- Vercel also has auto-created `NEON_*` vars from the integration; the app only reads `DATABASE_URL`

## Vercel deployment
- Entry point: `api/index.py` exposes `app.server` (Flask WSGI)
- Only env var needed on Vercel: `DATABASE_URL`
- Dashboard is read-only on Vercel — run `main.py` locally to update data
