from client_config import (
    AGENT_NAME, CLIENT_BRAND, OWNER_NAME,
    AGENT_PERSONA, QUALIFICATION_QUESTIONS,
    SEQUENCE_MESSAGES
)

def get_system_prompt(lead_summary: str) -> str:
    questions_text = "\n".join(
        [f"{i+1}. {q}" for i, q in enumerate(QUALIFICATION_QUESTIONS)]
    )
    return f"""
{AGENT_PERSONA}

Current lead profile:
{lead_summary}

Information you need to collect (weave naturally):
{questions_text}
"""

def get_extraction_prompt() -> str:
    return """
You are a silent data extraction engine. Return ONLY JSON.
No prose. No markdown. No code fences. Raw JSON only.

{
  "industry": null,
  "target_markets": null,
  "monthly_ad_budget": null,
  "ads_experience": null,
  "pain_point": null,
  "urgency": null,
  "preferred_call_time": null,
  "lead_score": null,
  "conv_status": null,
  "opted_out": false,
  "escalate": false,
  "close_intent": false
}

close_intent = true if lead says anything like:
"yes", "let's go", "I'm in", "send me the proposal",
"sounds good", "ready to start", "when can we begin",
"let's do it", "move forward"

opted_out = true if lead says anything like:
"not interested", "stop", "leave me alone", 
"fuck off", "don't message me", "remove me"

escalate = true if lead says:
"talk to a person", "speak to someone", "call me now",
"I want to speak to a human"

lead_score:
HOT = clear budget + urgent timeline + specific pain
WARM = vague budget OR soft timeline OR partial info
COLD = exploring only / no budget / disengaged
UNQUALIFIED = not enough info yet

conv_status values:
new / qualifying / stalled / awaiting_call /
post_call / fomo / cold / closed / upsell / 
archived / lost
"""

def get_sequence_message(key: str, **kwargs) -> str:
    template = SEQUENCE_MESSAGES.get(key, "")
    return template.format(**kwargs)
