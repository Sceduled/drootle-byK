# Pipecat Server Specification

Stack:
  Python + Pipecat framework
  STT: Deepgram Nova-2
  LLM: GPT-4o
  TTS: ElevenLabs (warm Indian-English female voice)
  Telephony: Twilio (SIP trunk)
  Hosting: DigitalOcean Droplet

Endpoints needed:
  POST /start-call → trigger outbound call
  GET  /health     → health check

Post-call:
  After call ends, Pipecat POSTs to callback_url with:
  { phone, lead_id, transcript, duration_seconds }

Agent voice persona (same as WhatsApp but adapted):
  - Shorter sentences (voice reads differently than text)
  - No emojis
  - Handles "who is this?" → "I'm the AI assistant calling from {CLIENT_BRAND}, we connected earlier about scaling your ads"
  - Same 7 qualification questions
  - Natural interruption handling (VAD)
  - Graceful hangup: "I'll have the team reach out at the time we discussed. Have a great day!"
