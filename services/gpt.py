"""
Service for interacting with OpenAI GPT models.
"""
import logging
import json
import asyncio
from openai import AsyncOpenAI

from core.config import settings
from prompts.agent import (
    get_system_prompt,
    get_extraction_prompt
)

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

async def call_gpt(messages: list, response_format: str = "text") -> str:
    if response_format == "json":
        sys_max_tokens = 800
        sys_temp = 0.1
        res_fmt = {"type": "json_object"}
    else:
        sys_max_tokens = 500
        sys_temp = 0.7
        res_fmt = {"type": "text"}
        
    for attempt in range(2):
        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=sys_max_tokens,
                temperature=sys_temp,
                response_format=res_fmt
            )
            
            usage = response.usage
            if usage:
                logger.info(f"GPT Token Usage - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")
                
            return response.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI API attempt {attempt+1} failed: {e}")
            if attempt < 1:
                await asyncio.sleep(1)
            else:
                logger.error("OpenAI API failed after retry.")
                if response_format == "json":
                    return "{}"
                else:
                    return "Thanks for that! Give me just a moment... 😊"

async def process_message(lead, conversation_history: list, new_message: str, is_voice: bool = False, language_instruction: str = "") -> tuple[str, dict]:
    logger.info(f"Running dual GPT-4o calls for lead_id: {lead.id} (is_voice={is_voice})")
    
    lead_summary = f"""
Industry: {lead.industry or 'not yet known'}
Target Markets: {lead.target_markets or 'not yet known'}
Monthly Ad Budget: {lead.monthly_ad_budget or 'not yet known'}
Ads Experience: {lead.ads_experience or 'not yet known'}
Pain Point: {lead.pain_point or 'not yet known'}
Urgency: {lead.urgency or 'not yet known'}
Preferred Call Time: {lead.preferred_call_time or 'not yet known'}
Lead Score: {lead.lead_score or 'not yet known'}
"""
    
    sys_prompt_conv = get_system_prompt(lead_summary)
    if language_instruction:
        sys_prompt_conv = f"{language_instruction}\n\n{sys_prompt_conv}"

    logger.info(f"System prompt length: {len(sys_prompt_conv)}")
    logger.info(f"System prompt preview: {sys_prompt_conv[:500]}")

    
    history_arr = []
    for conv in conversation_history:
        history_arr.append({
            "role": conv.role,
            "content": conv.content
        })
        
    messages_conv = [
        {"role": "system", "content": sys_prompt_conv}
    ] + history_arr
    if new_message:
        messages_conv.append({"role": "user", "content": new_message})
    
    if len(messages_conv) > 50:
        messages_conv = messages_conv[:5] + messages_conv[-45:]

    messages_ext = [
        {"role": "system", "content": get_extraction_prompt()}
    ] + history_arr
    if new_message:
        messages_ext.append({"role": "user", "content": new_message})
    
    if len(messages_ext) > 50:
        messages_ext = messages_ext[:5] + messages_ext[-45:]
        
    if is_voice:
        raw_extraction = await call_gpt(messages_ext, response_format="json")
        reply = ""
    else:
        reply_task = call_gpt(messages_conv, response_format="text")
        extract_task = call_gpt(messages_ext, response_format="json")
        reply, raw_extraction = await asyncio.gather(reply_task, extract_task)
    
    try:
        extraction = json.loads(raw_extraction)
    except Exception as e:
        logger.error(f"Extraction JSON parse failure: {e}. Raw: {raw_extraction}")
        extraction = {}
        
    return reply, extraction

async def call_gpt_mini(prompt: str) -> str:
    """Uses gpt-4o-mini for quick formatting tasks."""
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"call_gpt_mini failed: {e}")
        return "UNABLE_TO_PARSE"

async def generate_summary_from_history_text(history_text: str) -> str:
    prompt = f"""You are an expert sales assistant. Read the following WhatsApp conversation between an AI assistant and a lead.
Write a highly professional, 2-to-3 sentence executive summary of the lead's situation.
Focus on their pain points, what they are looking for, their budget (if mentioned), and timeline (if mentioned).
Do NOT write 'The lead says...' or 'The AI asked...'. Just state the facts directly as a professional CRM report.

Conversation:
{history_text}
"""
    return await call_gpt_mini(prompt)
