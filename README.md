# Agentic Lead AI

Agentic Lead AI is a fully autonomous AI sales and qualification agent specifically built for performance marketing campaigns. It intercepts inbound leads, qualifies them conversationally over WhatsApp (via Meta or OpenWA), scores them (HOT/WARM/COLD), and orchestrates downstream actions like Google Sheets updates, Sales team escalations, and automated call reminders.

---

## Architecture Overview

```text
[ Facebook/Instagram Ads ]
        │
[ Google Sheets Lead Form ]
        │
[ Make.com Webhook ] ──(POST /webhook/new-lead)──▶ [ FastAPI Backend ]
                                                            │
                                              [ ARQ Redis Queue ]
                                                            │
[ Meta / OpenWA ] ◀──(Send Opening Msg via Worker)──────────┘
        │
[ User Replies ] ──(POST /webhook/whatsapp)──▶ [ FastAPI Backend ]
                                                            │
                                        [ Redis Buffer (Concurrency Control) ]
                                                            │
[ OpenAI GPT-4o ] ◀──(Extract & Qualify via Worker)─────────┘
        │
(If Qualified)
  ├─▶ [ Update Google Sheet via Async API ]
  ├─▶ [ WhatsApp Sales Team Alert ]
  └─▶ [ Schedule Pre-Call Reminder ]
```

---

## Tech Stack
- **Backend**: Python 3.10+, FastAPI
- **Database**: PostgreSQL (SQLAlchemy Async ORM, Alembic)
- **Background Jobs**: ARQ + Redis
- **AI**: OpenAI `gpt-4o` and `gpt-4o-mini`
- **Frontend**: React 18, Vite, TailwindCSS v4, Recharts
- **Integrations**: Meta Cloud API, OpenWA, Google Sheets API, Bolna, Pipecat

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Postgres async URL (e.g. `postgresql+asyncpg://user:pass@localhost:5432/db`) | Yes |
| `REDIS_URL` | Redis URL (e.g. `redis://localhost:6379/0`) | Yes |
| `OPENAI_API_KEY` | Your OpenAI API key | Yes |
| `OPENAI_MODEL` | GPT model to use (default: `gpt-4o`) | Yes |
| `WHATSAPP_PROVIDER` | `meta` or `openwa` | Yes |
| `META_WHATSAPP_TOKEN` | Meta API permanent access token | If using Meta |
| `META_PHONE_NUMBER_ID` | Meta Business Phone Number ID | If using Meta |
| `META_WEBHOOK_VERIFY_TOKEN` | Custom token for Meta webhook verification | If using Meta |
| `META_APP_SECRET` | App Secret from Meta Developer console for HMAC validation | If using Meta |
| `OPENWA_URL` | OpenWA endpoint (e.g., `http://localhost:3000`) | If using openWA |
| `OPENWA_API_KEY` | OpenWA auth key | If using openWA |
| `GOOGLE_SHEET_ID` | ID of the Google Sheet for writes | Yes |
| `GOOGLE_CREDENTIALS_JSON` | Stringified JSON of Google Service Account | Yes |
| `SALES_TEAM_WHATSAPP_NUMBERS` | Comma-separated list of sales reps numbers | Yes |
| `JWT_SECRET` | Secret string to sign frontend dashboard tokens | Yes |
| `JWT_EXPIRY_HOURS` | Expiry time for dashboard login | Yes |
| `WEBHOOK_SECRET` | Secret expected in Make.com header `X-Webhook-Secret` | Yes |
| `DASHBOARD_USERNAME` | Username for React Admin Panel | Yes |
| `DASHBOARD_PASSWORD` | Password for React Admin Panel | Yes |
| `VOICE_ENABLED` | `true` or `false` to enable AI voice | Yes |
| `VOICE_PROVIDER` | `bolna` or `pipecat` | If voice enabled |
| `VOICE_TRIGGER` | `manual`, `no_reply_2h`, or `reminder` | If voice enabled |
| `BOLNA_API_KEY` / `BOLNA_AGENT_ID` | Bolna credentials | If using Bolna |
| `PIPECAT_SERVER_URL` | Pipecat hosted server URL | If using Pipecat |

---

## Running Locally

1. **Spin up Postgres and Redis using Docker:**
   ```bash
   docker run -d --name pg-drootle -e POSTGRES_USER=drootle -e POSTGRES_PASSWORD=pass -e POSTGRES_DB=drootle -p 5432:5432 postgres:15
   docker run -d --name redis-drootle -p 6379:6379 redis:alpine
   ```

2. **Install Python Dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Run Database Migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start the FastAPI Server:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Start the ARQ Background Worker (in a separate terminal):**
   ```bash
   arq workers.tasks.WorkerSettings
   ```

6. **Start the React Frontend (in a separate terminal):**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## Deploying to Railway

1. Create a new Railway project.
2. Provision **PostgreSQL** and **Redis** plugins.
3. Link your GitHub repository.
4. Set all required Environment Variables (see table above).
5. Railway handles the web service build automatically (Procfile/uvicorn).
6. **Worker Service Setup**: Add a second service from the same repo. Override the Start Command to:
   ```bash
   arq workers.tasks.WorkerSettings
   ```
7. Ensure `RAILWAY_PUBLIC_DOMAIN` is set to your app's public URL for Pipecat/Bolna webhooks.

---

## Enabling Voice

The Voice layer (Pipecat/Bolna) is completely dormant by default. To activate:

1. Set `VOICE_ENABLED=true`
2. Set `VOICE_PROVIDER` to either `bolna` or `pipecat`.
3. Set `VOICE_TRIGGER` to your preferred behavior:
   - `manual`: Only triggered via Dashboard button.
   - `no_reply_2h`: Automatically calls leads who go dark for 2 hours.
   - `reminder`: Automatically calls exactly when their scheduled call reminder fires.
4. Add the respective provider keys (`BOLNA_API_KEY` + `BOLNA_AGENT_ID` OR `PIPECAT_SERVER_URL`).

---

## Make.com Setup

1. Create a Make.com scenario triggered by Facebook Lead Ads.
2. Add an HTTP Request node.
3. **URL**: `https://<your-domain>/api/webhook/new-lead`
4. **Method**: `POST`
5. **Headers**:
   - `X-Webhook-Secret`: `<your WEBHOOK_SECRET>`
   - `Content-Type`: `application/json`
6. **Body**:
   ```json
   {
     "name": "{{1.full_name}}",
     "phone": "{{1.phone_number}}",
     "email": "{{1.email}}",
     "company": "{{1.company_name}}",
     "source_ad": "{{1.ad_name}}",
     "sheet_row": "{{2.row_number}}" 
   }
   ```
*(Assuming module 2 is a Google Sheets "Add Row" node.)*

---

## Meta WhatsApp Setup (Direct Connection or Custom API)

1. Go to Facebook Developer Console -> App -> WhatsApp -> Configuration.
2. Set the **Callback URL** to `https://<your-domain>/api/webhook/whatsapp`
3. Set the **Verify Token** to match your `META_WEBHOOK_VERIFY_TOKEN`.
4. Subscribe to the `messages` webhook field.
5. In App settings, get the **App Secret** and put it in `META_APP_SECRET`.
6. Get your permanent token and Phone Number ID from the API Setup page and place them in your `.env`.

---

## Vobiz Setup (Client WABA ID)

When a client provides their own WhatsApp Business API (WABA) ID, you can use Vobiz via Direct Connection to connect instantly without migrating phone numbers.

1. Set `WHATSAPP_PROVIDER=vobiz` in your `.env`.
2. Give Vobiz your backend webhook URL: `https://<your-domain>/api/webhook/whatsapp`.
3. Vobiz internally maps to the exact same Meta Cloud API payloads, so the backend handles it natively. No further API changes are needed.

---

## openWA Setup (Alternative to Meta)

1. Deploy openWA locally or on a server.
2. Generate an API Key in the openWA dashboard.
3. Add the Webhook URL in openWA: `https://<your-domain>/api/webhook/whatsapp-owa`
4. Configure your `.env`:
   - `WHATSAPP_PROVIDER=openwa`
   - `OPENWA_URL=<your-openwa-ip:3000>`
   - `OPENWA_API_KEY=<your-key>`
5. Scan the QR code in openWA using the WhatsApp app on a physical device.
