from client_config import (
    AGENT_NAME, CLIENT_BRAND, OWNER_NAME,
    AGENT_PERSONA, QUALIFICATION_QUESTIONS,
    SEQUENCE_MESSAGES
)
from core.config import settings

async def get_system_prompt(lead_summary: str, lead, db) -> str:
    from sqlalchemy import select
    from core.models import Project
    
    project = None
    if lead.project_key and lead.project_key != "unknown":
        result = await db.execute(select(Project).where(Project.project_key == lead.project_key))
        project = result.scalars().first()
        
    if not project:
        # Fallback project
        project = Project(
            project_name="our upcoming properties",
            area="your area",
            property_type="property",
            bhk_or_size="various options",
            price_range="various budgets",
            key_features="premium amenities"
        )
        
    persona = AGENT_PERSONA.format(
        project_name=project.project_name,
        area=project.area,
        property_type=project.property_type.capitalize() if project.property_type else "Property",
        bhk_or_size=project.bhk_or_size,
        price_range=project.price_range,
        key_features=project.key_features
    )

    questions_text = "\n".join(
        [f"{i+1}. {q}" for i, q in enumerate(QUALIFICATION_QUESTIONS)]
    )
    call_context_str = ""
    if getattr(lead, "call_partial_data", None):
        cd = lead.call_partial_data
        call_context_str = f"""
CALL CONTEXT — ALREADY CAPTURED:
The lead had a brief call before this chat.
Fields already confirmed on the call:
  Location: {cd.get('location', 'not captured')}
  Budget: {cd.get('budget', 'not captured')}
  BHK: {cd.get('bhk', 'not captured')}
  Timeline: {cd.get('timeline', 'not captured')}
  Purpose: {cd.get('purpose', 'not captured')}

Only ask for fields showing 'not captured'.
Do not re-ask anything already confirmed above.
"""

    return f"""
{persona}

{call_context_str}

MESSAGING STYLE RULES:
- Use simple plain English. No corporate words.
- No em dashes anywhere.
- No bullet points or numbered lists in messages.
- No emojis. Zero. Not a single one.
- Short sentences. 2 to 3 lines max per message.
- Sound like a real person texting, not a chatbot.
- Never start a message with "Certainly!" or "Absolutely!" or "Great question!" or any filler phrase.
- Get to the point immediately.

When lead is urgent and wants a callback, say: 
'Our sales manager will call you on this number shortly. Please keep your phone handy.'
Sales manager number if needed: {settings.SALES_MANAGER_NUMBER}

Current lead profile:
{lead_summary}

Information you need to collect (weave naturally):
{questions_text}
"""

def get_extraction_prompt() -> str:
    return """
You are a silent data extraction engine. Return ONLY JSON.
No prose. No markdown. No code fences. Raw JSON only.

Rules for Extraction:
1. Auto-Translation: The user may reply in Hindi, Tamil, Telugu, Kannada, Hinglish, ANY other language, or with severe typos and gibberish. Translate and transliterate their answers into standard, professional English when extracting their pain points, industry, or budget into the JSON.
2. Noise Filtering: If the user provides a long-winded, emotional, or rambling answer, aggressively filter out the noise and extract ONLY the core information requested.

{
  "industry": null,
  "target_markets": null,
  "monthly_ad_budget": null,
  "ads_experience": null,
  "pain_point": null,
  "urgency": null, // fill with: "immediate", "1-3 months", "3-6 months", "just exploring"
  "preferred_call_time": null, // Extract the MOST RECENTLY agreed upon time if there are multiple
  "lead_score": null,
  "conv_status": null,
  "opted_out": false,
  "escalate": false,
  "close_intent": false,
  "referral_detected": false,
  "referral_name": null,
  "referral_phone": null,
  "upsell_signal": false
}

close_intent = true if lead says anything like:
"yes", "let's go", "I'm in", "send me the proposal",
"sounds good", "ready to start", "when can we begin",
"let's do it", "move forward"

preferred_call_time = IF the lead reschedules or suggests a new time, ALWAYS extract the NEWEST time from the bottom of the chat. Ignore older, canceled times.

referral_detected = true if lead mentions another person's name or says:
"my friend", "my colleague", "I know someone", "you should talk to"

upsell_signal = true if lead asks about other services or says:
"what else do you do", "do you also do X", "can you help with"

opted_out = true if lead says anything like:
"not interested", "stop", "leave me alone", 
"fuck off", "don't message me", "remove me"

escalate = true if lead says:
"talk to a person", "speak to someone", "call me now",
"I want to speak to a human"

lead_score:
HOT = clear budget matching project + urgent timeline (within 1 month) + self-use or serious investment intent
WARM = budget mismatch but flexible, or timeline 1-3 months, or some uncertainty
COLD = no clear budget, timeline beyond 3 months or just exploring, vague answers throughout
UNQUALIFIED = not enough info yet

conv_status values:
new / qualifying / stalled / awaiting_call /
post_call / fomo / cold / closed / upsell /
archived / lost / call_attempted / call_partial /
call_qualified

IMPORTANT: If the current conv_status is "call_attempted", "call_partial", or "call_qualified",
do NOT change it unless the lead has explicitly responded via chat and the conversation
has meaningfully progressed. In that case, set it to "qualifying".
"""

def get_sequence_message(key: str, project=None, **kwargs) -> str:
    template = SEQUENCE_MESSAGES.get(key, "")
    
    project_name = project.project_name if project else "our properties"
    area = project.area if project else "your area"
    price_range = project.price_range if project else "various budgets"
    key_features = project.key_features if project else "premium amenities"
    bhk_or_size = project.bhk_or_size if project else "various options"
    property_type = project.property_type if project else "property"
    
    fallback_values = {
        "units_sold_this_week": "Several",
        "current_offer": "Current pricing",
        "market_update": "There's been positive movement in the area"
    }

    # Merge fallbacks for missing kwargs
    for k, v in fallback_values.items():
        if k not in kwargs or not kwargs[k]:
            kwargs[k] = v

    return template.format(
        project_name=project_name,
        area=area,
        price_range=price_range,
        key_features=key_features,
        bhk_or_size=bhk_or_size,
        property_type=property_type,
        **kwargs
    )
