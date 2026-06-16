# client_config.py — DROOTLE (Performance Marketing Agency)
# To deploy for a new client: edit ONLY this file.

# ─── AGENT IDENTITY ───────────────────────────────────────────
AGENT_NAME = "Maya"
CLIENT_BRAND = "Drootle"
OWNER_NAME = "Dharshaan Jade"

AGENT_PERSONA = """
You are Maya, a friendly and sharp assistant working for Drootle 
— a performance marketing agency that turns ad spends into 
investments for businesses in real estate, home improvement, 
healthcare, and construction across India, USA, Canada, 
Australia, and New Zealand.

Your job is to qualify inbound leads before they speak with 
Darshaan's team. You are warm, professional, and concise. 
You do not pitch. You gather information naturally.

Rules:
- Ask one question at a time maximum
- Keep messages to 2-3 sentences max
- Use light, natural punctuation. No corporate speak.
- If they ask about pricing: say "Darshaan will walk you 
  through everything on the call"
- If they say not interested: acknowledge gracefully, close warmly
- If they ask to speak to a human: say you will flag it now
- Never make up facts about the client's pricing or guarantees
- Never ask a question already answered
"""

# ─── QUALIFICATION QUESTIONS ──────────────────────────────────
# Maya weaves these naturally — never as a form, never all at once
QUALIFICATION_QUESTIONS = [
    "What industry or niche is your business in?",
    "Which markets are you targeting?",
    "What's your monthly ad budget roughly?",
    "Have you run paid ads before?",
    "What's the main problem with your lead gen right now?",
    "How urgently are you looking to start?",
    "What's the best time for Darshaan to give you a call?",
]

# ─── SEQUENCE MESSAGES ────────────────────────────────────────
# {name}, {time}, {score}, {industry}, {budget}, 
# {phone}, {pain_point} are available as placeholders

SEQUENCE_MESSAGES = {
    # Sequence 1 — First Touch
    "first_touch": (
        "Hi {name}! 👋 I'm Maya from Drootle. "
        "You reached out about scaling your business with ads. "
        "Quick 2-min chat to prep Darshaan's team? 😊"
    ),

    # Sequence 2 — Qualification nudges (AI drives, these are fallbacks)
    "qual_nudge_24h": (
        "Hey {name}! Just checking in — still around? 😊"
    ),
    "reschedule_ask": (
        "Hey {name}, Darshaan mentioned we need to reschedule our call. What time works best for you?"
    ),

    # Sequence 3 — DNP Recovery
    "dnp_day1": (
        "Hey {name}, just checking in — "
        "still happy to connect! 😊"
    ),
    "dnp_day2": (
        "Thought this might be useful — one of our clients "
        "in a similar space went from 50 leads/month to 300 "
        "just by fixing their targeting. Happy to share more."
    ),
    "dnp_day3": (
        "No worries if timing isn't right — "
        "just let me know and I'll keep this open for you 🙏"
    ),
    "dnp_day5": (
        "I'll be closing your file by end of day unless I "
        "hear back — just so I don't keep bothering you 🙏"
    ),

    # Sequence 4 — Call Reminders
    "call_reminder_lead": (
        "Hi {name}! Just a reminder — Darshaan's team will "
        "be calling you at {time} today 🙌 Looking forward to it!"
    ),
    "call_reminder_sales": (
        "📞 Call {name} NOW\n"
        "{score}\n"
        "Industry: {industry}\n"
        "Budget: {budget}\n"
        "Pain: {pain_point}\n"
        "Phone: {phone}"
    ),

    # Sequence 5 — Post-Call Validation
    "post_call_day1": (
        "Great speaking today {name}! "
        "Here's what we discussed and what comes next... "
        "Darshaan's team will send over the details shortly 🙌"
    ),
    "post_call_day2": (
        "Thought you'd find this relevant — "
        "one of our {industry} clients saw 3x lead quality "
        "within the first month. Happy to share the full story."
    ),
    "post_call_day3": (
        "Here's what one of our clients had to say: "
        "'Drootle completely changed how we think about leads.' "
        "We'd love to do the same for you {name} 🙏"
    ),
    "post_call_day5": (
        "I know {pain_point} has been a challenge — "
        "we've solved this for several clients in your space. "
        "Here's how we approached it..."
    ),
    "post_call_day7": (
        "Ready to get started {name}? "
        "We can kick things off as early as next week 🚀 "
        "Just say the word and Darshaan will take it from here."
    ),

    # Sequence 6 — FOMO Creation
    "fomo_day1": (
        "We only onboard 3 clients per month in your niche — "
        "two spots are already taken for this month."
    ),
    "fomo_day2": (
        "Two other businesses in your space started with us "
        "this week — just so you have the full picture 🙏"
    ),
    "fomo_day3": (
        "Happy to hold your spot until Friday. "
        "After that it goes to the next person on the list — "
        "no pressure either way 🙏"
    ),

    # Sequence 7 — Lead Recovery / Reactivation
    "reactivation_wk2": (
        "3 things most agencies get wrong with Meta ads "
        "in your niche — thought this might be useful 👇"
    ),
    "reactivation_wk4": (
        "What we're seeing in your space this month — "
        "thought you'd find this interesting."
    ),
    "reactivation_wk6": (
        "Things change fast — still exploring growth options "
        "or have you sorted it out? 😊"
    ),
    "reactivation_wk8": (
        "We recently started working with a client who had "
        "the exact same challenge you mentioned. "
        "Mind if I share what worked for them?"
    ),
    "reactivation_wk12": (
        "Closing this conversation after today — "
        "anything changed on your end? 🙏"
    ),

    # Sequence 8 — Closed / Referral + Review
    "closed_day3": (
        "Excited to get started {name}! "
        "Here's what happens next and what to expect "
        "in the first 30 days 🙌"
    ),
    "closed_wk2": (
        "How are things going so far {name}? "
        "Anything you need from us?"
    ),
    "closed_mo1": (
        "Quick favour {name} — know anyone who'd benefit "
        "from this? Happy to take care of them like we did you 🙏"
    ),
    "closed_mo1_fup": (
        "Would you mind sharing a quick review? "
        "Even 2 sentences helps us massively 🙏"
    ),

    # Sequence 9 — Upsell / Cross-sell
    "upsell_day1": (
        "Since your ads are running well {name}, "
        "have you thought about adding SEO to the mix? "
        "We've seen great results combining both."
    ),
    "upsell_day4": (
        "One of our clients who combined ads + SEO "
        "saw a 40% drop in cost per lead within 60 days. "
        "Happy to share the full breakdown."
    ),
    "upsell_day7": (
        "Want me to have Darshaan walk you through it "
        "on a quick 15-min call? No pressure at all 😊"
    ),
}
