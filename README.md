# Punch Portal

Upload a punched NRLDC/WRLDC schedule CSV → the portal auto-detects the plant
(entity), works out which 2 blocks you just punched (using the +1h45m,
floor-to-15-min rule), and emails the configured recipients with the file
attached.

## How the block logic works

    target = punch_time + 1 hour 45 minutes
    round target DOWN to the nearest 15-minute mark  -> first punched block
    the next 15-minute block is the second punched block

Examples: 8:16 → blocks 10:00-10:15 & 10:15-10:30. 10:58 → blocks
12:30-12:45 & 12:45-13:00. This matches how the actual "punch time" you're
sitting at maps to the just-opened blocks on the REMC portal.

## What the portal does on upload

1. Reads the `Scheduling entity` value from the CSV — that's how it knows
   which plant this is, no filename convention needed.
2. Looks it up in the entities table.
   - **Known entity** → shows a preview (blocks, values, recipients, email
     text) and a **Send email now** button.
   - **Unknown entity** → lets you fill in display name, region, recipients,
     and email templates right there, then sends immediately after saving.
3. Sends the email (with the CSV attached) over your company SMTP server.
4. Logs every send (entity, blocks, recipients, status) under **Send Log**.

## Adding more plants later

Go to **Manage Entities** → add a new entity manually (or just upload a CSV
for a plant that isn't configured yet — the inline form handles it). Each
entity has its own:

- Entity key (must match the `Scheduling entity` cell in that plant's CSV)
- Display name / region
- List of recipient emails (add/remove any time)
- Email subject & body template, editable any time via **Modify template**

Template placeholders you can use in subject/body:
`{entity_key} {display_name} {date} {revision} {punch_time} {blocks_table} {filename}`

## Setup

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml with your company SMTP host/port/login
streamlit run app.py
```

The database (`data/portal.db`, SQLite) is created automatically on first
run and holds all entities/recipients/templates/logs — back it up if you
redeploy.

## Hosting (pick whichever is easiest for you)

**Option A — Streamlit Community Cloud (free, simplest)**
1. Push this folder to a GitHub repo (private is fine).
2. Go to share.streamlit.io → "New app" → point it at the repo/`app.py`.
3. In the app's "Secrets" settings, paste the contents of your
   `secrets.toml` (SMTP host/port/username/password).
4. Done — you get a URL you can open from anywhere.

Note: on Streamlit Community Cloud, the filesystem (and so the SQLite DB)
resets on redeploy/restart. Fine for testing; for production use Option B or
point `DB_PATH` in `db.py` at a small persistent disk.

**Option B — A small VPS / Render / Railway (persistent storage)**
1. Any $5-7/month box works. Install Python 3.11+, `pip install -r requirements.txt`.
2. Run behind a process manager: `streamlit run app.py --server.port 8501 --server.address 0.0.0.0`
   (use `pm2`, `systemd`, or the platform's built-in process manager).
3. Put it behind a reverse proxy (Caddy/Nginx) for HTTPS + a real domain, or
   use Render/Railway's built-in HTTPS.
4. Set the SMTP secrets via the platform's environment/secrets manager, or
   just keep `.streamlit/secrets.toml` on the box (don't commit it to git).

Either way, storage is a single SQLite file — no database server to manage.
