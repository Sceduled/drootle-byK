# New Client Launch Checklist
Estimated time: 3-4 hours

## Step 1 — Duplicate repo (5 min)
  git clone drootle-byk new-client-name
  cd new-client-name
  git remote set-url origin https://github.com/Sceduled/new-client-name
  git push -u origin main

## Step 2 — Fill client_config.py (45 min)
  Open `client_config.py`
  Change: AGENT_NAME, CLIENT_BRAND, OWNER_NAME
  Rewrite: AGENT_PERSONA for this client's niche
  Rewrite: QUALIFICATION_QUESTIONS (keep exactly 7)
  Rewrite: SEQUENCE_MESSAGES for this client's context
  Give context to coding agent → it rewrites the file

## Step 3 — Railway setup (20 min)
  Create new Railway project
  Add services: FastAPI + ARQ Worker + PostgreSQL + Redis
  Set all env vars (see env var list below)
  Deploy

## Step 4 — Google Sheets (20 min)
  Create leads sheet with headers:
    name | phone | email | company | source_ad
  Share with service account email
  Add GOOGLE_SHEET_ID to Railway vars

## Step 5 — WhatsApp connection (30 min)
  Option A (WAHA): Deploy WAHA Docker service,
    scan QR, set WAHA_URL + WAHA_API_KEY
  Option B (Meta/Vobiz): Get WABA ID from client,
    set VOBIZ credentials
  Set WHATSAPP_PROVIDER accordingly

## Step 6 — Apps Script trigger (10 min)
  Open Google Sheet → Extensions → Apps Script
  Paste script from `scripts/google_apps_script.js`
  Update WEBHOOK_SECRET and URL
  Run `createTrigger()`

## Step 7 — Register with admin (5 min)
  Add client to admin_db client_registry table
  Set CLIENT_ID and CLIENT_NAME env vars

## Step 8 — Test end to end (60 min)
  Add test row to sheet → WhatsApp arrives in 60s
  Reply as lead → qualify fully → check dashboard
  Trigger call reminder → verify sales alert
  Test opt-out → verify everything stops
  Check admin dashboard shows this client

## Step 9 — Hand over (10 min)
  Share dashboard URL + login credentials
  Share sales team WA number setup confirmation
  Done

## Required env vars
(full list here matching `.env.example`)
