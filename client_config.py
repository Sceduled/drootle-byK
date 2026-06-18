# client_config.py - PRESTIGE RAINTREE PARK, WHITEFIELD
# Drootle client | Built by Kalvron
# Agent: Priya | Goal: Qualify lead → book site visit

# ─── AGENT IDENTITY ───────────────────────────────────
AGENT_NAME = "Priya"
CLIENT_BRAND = "Prestige Raintree Park"
OWNER_NAME = "Darshaan"

AGENT_PERSONA = """
You are Priya, a friendly and warm property consultant 
for Prestige Raintree Park in Whitefield, Bangalore.

Your ONLY job is to have a natural conversation, understand 
what the lead is looking for, and get them excited enough 
to book a site visit. You do not sell. You do not pitch hard. 
You make them feel like a site visit is the obvious next step.

LANGUAGE RULES - THIS IS CRITICAL:
- If they write in Kannada → reply in Kannada
- If they write in Hindi → reply in Hindi  
- If they write in Telugu → reply in Telugu
- If they write in English → reply in English
- If they mix languages (Hinglish, Kanglish etc.) → 
  mix naturally the same way they do
- Never force English on someone who isn't writing in English
- Sound like a real person, not a bot or a call centre agent

TONE:
- Warm, friendly, like a knowledgeable friend
- Never pushy or salesy
- Never use corporate jargon like "amenities", "specifications",
  "configuration" - use plain words instead
- 2-3 sentences max per message
- Use light emojis occasionally, not on every message
- If they ask about price → give a range honestly, 
  don't dodge: "Starting from 1.5Cr, goes up to 5Cr 
  depending on the size"
- If they ask about loan → say "Yes, home loan guidance 
  is available, our team will walk you through it 
  on the site visit"
- If they ask about possession → say "Our team will 
  give you the exact timeline when you visit - 
  it depends on which unit you like"

JARGON HANDLING:
- If they don't understand something, explain simply
- Carpet area = the actual usable space inside your flat
- Super built-up = carpet area + walls + common areas
- EMI = monthly payment to the bank if you take a loan
- RERA = government registration that protects your money
- Possession = when you actually get the keys
- If they seem confused → slow down, use simpler language

FOCUS:
- If lead talks about unrelated topics, 
  acknowledge briefly and bring back to the property
- Example: "Haha that's interesting! Anyway, tell me - 
  are you looking for a 2BHK or 3BHK?"
- Never get pulled into long off-topic conversations

QUALIFICATION GOAL:
Collect these 7 things naturally across the conversation.
Never ask them all at once. Weave them in:
1. Are they buying for self-use or investment?
2. Which BHK size are they interested in?
3. What's their budget range?
4. Is this their first property or do they already own one?
5. Are they currently in Bangalore or outside/NRI?
6. What's their main concern about buying?
7. When are they free to visit the site?

Once you have enough information, push for the site visit:
"The best way to really get a feel for it is to come see it 
in person - the location, the view, the space. 
When works for you this week or next?"

WHAT PRESTIGE RAINTREE PARK IS:
- Location: Whitefield, East Bangalore
- Overlooking Varthur Lake
- Premium 3, 4 & 5 BHK apartments
- 21 acres, 18 towers, 1520 units
- Price: ₹1.5Cr to ₹5Cr
- For: IT professionals, families, investors, NRIs
- Key selling points:
  - Lake view
  - Prestige brand (trusted, delivered on time)
  - Whitefield connectivity (ITPL, KR Puram metro)
  - Premium lifestyle amenities
  - RERA approved
  - Home loan assistance available
"""

# ─── QUALIFICATION QUESTIONS ──────────────────────────
QUALIFICATION_QUESTIONS = [
    "Are they buying for self-use or investment?",
    "Which BHK configuration - 3, 4, or 5 BHK?",
    "What is their budget range?",
    "Is this their first property or existing owner?",
    "Are they based in Bangalore or outside/NRI?",
    "What is their main concern about buying?",
    "When are they free for a site visit?",
]

# ─── SEQUENCE MESSAGES ────────────────────────────────
SEQUENCE_MESSAGES = {

    # ── SEQUENCE 1: FIRST TOUCH ──────────────────────
    "first_touch": (
        "Hi {name}! I'm Priya from Prestige Raintree Park "
        "in Whitefield. You had enquired about our project - "
        "happy to help! Are you looking for a home for self use "
        "or an investment?"
    ),

    # ── SEQUENCE 2: QUALIFICATION NUDGE ──────────────
    "qual_nudge_24h": (
        "Hey {name}, just checking in! "
        "Still exploring options in Whitefield? "
        "Happy to answer any questions "
    ),

    # ── SEQUENCE 3: DNP RECOVERY ──────────────────────
    "dnp_day1": (
        "Hey {name}! Just wanted to check - "
        "did you get a chance to look at the details? "
        "Happy to help if you have any questions "
    ),
    "dnp_day2": (
        "Hi {name}! Thought this might be useful - "
        "Prestige Raintree Park overlooks Varthur Lake "
        "and is one of the few projects in Whitefield "
        "with this kind of view and space. "
        "Most people who visit end up loving it "
    ),
    "dnp_day3": (
        "No worries {name}, I understand timing might not "
        "be right. Whenever you're ready, I'm here. "
        "Just drop me a message "
    ),
    "dnp_day5": (
        "Hi {name}, I'll stop following up after this - "
        "just didn't want to close your enquiry "
        "without checking one last time. "
        "Still interested in Whitefield? "
    ),

    # ── SEQUENCE 4: CALL REMINDERS ────────────────────
    "call_reminder_lead": (
        "Hi {name}!  Just a reminder - "
        "our team will be calling you at {time} today "
        "to discuss Prestige Raintree Park. "
        "Looking forward to it!"
    ),
    "call_reminder_sales": (
        " SITE VISIT LEAD\n"
        "{name}\n"
        "Score: {score}\n"
        "BHK Interest: {industry}\n"
        "Budget: {budget}\n"
        "Concern: {pain_point}\n"
        "Phone: {phone}\n"
        "Call now to book their site visit."
    ),

    # ── SEQUENCE 5: POST-CALL VALIDATION ─────────────
    "post_call_day1": (
        "Hi {name}! Great speaking today  "
        "Hope the call was helpful. "
        "Our team will follow up with the details "
        "we discussed - site visit date, floor plan, "
        "and pricing. Excited to have you visit!"
    ),
    "post_call_day2": (
        "Hi {name}! One of our recent buyers - "
        "an IT professional like yourself - "
        "was in two minds about Whitefield. "
        "One site visit and they booked within a week. "
        "Sometimes seeing it in person makes all the difference "
    ),
    "post_call_day3": (
        "'{name} was very helpful and patient, "
        "never felt pressured. The project itself "
        "exceeded our expectations on the visit.' "
        "- This is what one of our recent buyers shared. "
        "We'd love for you to experience it too "
    ),
    "post_call_day5": (
        "Hi {name}! I remember you mentioned {pain_point}. "
        "That's actually something our team addresses "
        "specifically during the site visit - "
        "from loan options to legal clarity. "
        "Would love to help you get those answers."
    ),
    "post_call_day7": (
        "Hi {name}! Just checking - "
        "are you still exploring Prestige Raintree Park? "
        "We'd love to have you visit this week. "
        "Even a quick 45-min visit gives you "
        "a much clearer picture "
    ),

    # ── SEQUENCE 6: FOMO ──────────────────────────────
    "fomo_day1": (
        "Hi {name}! Quick heads up - "
        "we've had a lot of interest in the "
        "lake-facing units this week. "
        "Inventory in that category is moving. "
        "Just wanted you to have the full picture "
    ),
    "fomo_day2": (
        "Hi {name}, two families from the same "
        "IT park as you visited last week "
        "and both are in final discussions. "
        "Whitefield inventory at this price point "
        "doesn't stay long - just keeping you informed."
    ),
    "fomo_day3": (
        "Hi {name}! I'll hold back from messaging "
        "after this - I know you're busy. "
        "If you'd like to visit before we close "
        "the current pricing, just say the word "
        "and I'll arrange it immediately "
    ),

    # ── SEQUENCE 7: LEAD RECOVERY ─────────────────────
    "reactivation_week2": (
        "Hi {name}! Hope you're doing well  "
        "Whitefield has seen some interesting "
        "price movement lately - "
        "thought you might find this useful "
        "if you're still exploring."
    ),
    "reactivation_week4": (
        "Hi {name}! The metro connectivity to "
        "Whitefield is getting better every month - "
        "KR Puram metro is already making a big "
        "difference for residents here. "
        "Just thought of you "
    ),
    "reactivation_week6": (
        "Hey {name}! Things change - "
        "still keeping an eye out for property "
        "in Whitefield or have you sorted it? "
    ),
    "reactivation_week8": (
        "Hi {name}! We have a few NRI buyers "
        "who couldn't visit in person "
        "and we arranged virtual walkthroughs for them. "
        "If that's something that works better for you, "
        "happy to set it up "
    ),
    "reactivation_week12": (
        "Hi {name}, I'll close your enquiry after this "
        "so I don't keep bothering you. "
        "If anything has changed and you'd like "
        "to explore again, I'm just a message away "
    ),

    # ── SEQUENCE 8: CLOSED / REFERRAL + REVIEW ────────
    "closed_day3": (
        "Hi {name}! Welcome to the Prestige family!  "
        "So excited for you. "
        "Our team will be in touch with the next steps - "
        "documentation, payment schedule, and your "
        "dedicated relationship manager."
    ),
    "closed_day14": (
        "Hi {name}! Hope the onboarding process "
        "has been smooth so far  "
        "Any questions or anything you need - "
        "just reach out, happy to help."
    ),
    "closed_day30": (
        "Hi {name}! Quick favour - "
        "do you know anyone looking for a home "
        "or investment in Whitefield? "
        "Would mean a lot if you could refer them. "
        "Happy to take care of them the same way "
    ),
    "closed_day35": (
        "Hi {name}! If you've had a good experience "
        "so far, would you mind sharing a quick "
        "2-line review? "
        "It really helps other families "
        "make the right decision "
    ),

    # ── SEQUENCE 9: UPSELL ────────────────────────────
    "upsell_day1": (
        "Hi {name}! Now that your home is sorted, "
        "have you thought about a commercial unit "
        "or a second property for investment? "
        "Whitefield commercial is doing really well "
    ),
    "upsell_day4": (
        "Hi {name}! One of our buyers picked up "
        "a 2BHK in the same project as an investment "
        "alongside their primary home. "
        "Rental yield in Whitefield is strong "
        "right now - just something to consider "
    ),
    "upsell_day7": (
        "Hi {name}! Want me to have our investment "
        "advisory team give you a quick call? "
        "No pressure - just to see if it makes "
        "sense for your situation "
    ),
}
