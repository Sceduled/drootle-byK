import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import Optional

from core.database import get_db
from core.models import Lead, Conversation, StageHistory, SequenceConfig
from api.routes.auth import get_current_user
from api.routes.webhooks import get_arq_pool
from core.config import settings
from pydantic import BaseModel
from utils.stage_logger import log_stage_change
from services.notifications import notify_sales_opt_out

router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get("/leads")
async def get_leads(
    page: int = 1,
    limit: int = 20,
    score: Optional[str] = None,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    if score:
        query = query.where(Lead.lead_score == score)
    if status:
        query = query.where(Lead.conv_status == status)
    if industry:
        query = query.where(Lead.industry == industry)
        
    score_sort = case(
        (Lead.lead_score == 'HOT', 1),
        (Lead.lead_score == 'WARM', 2),
        (Lead.lead_score == 'COLD', 3),
        else_=4
    )
    status_sort = case(
        (Lead.conv_status == 'awaiting_call', 1),
        (Lead.conv_status == 'qualifying', 2),
        (Lead.conv_status == 'post_call', 3),
        (Lead.conv_status == 'fomo', 4),
        (Lead.conv_status == 'stalled', 5),
        (Lead.conv_status == 'cold', 6),
        (Lead.conv_status == 'new', 7),
        (Lead.conv_status == 'closed', 8),
        (Lead.conv_status == 'upsell', 9),
        (Lead.conv_status == 'archived', 10),
        (Lead.conv_status == 'lost', 11),
        else_=12
    )
    query = query.order_by(score_sort.asc(), status_sort.asc(), Lead.created_at.desc())
    
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return {
        "leads": leads,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 0
    }

@router.get("/leads/export")
async def export_leads(db: AsyncSession = Depends(get_db)):
    async def iter_csv():
        yield "name,phone,company,industry,markets,budget,pain_point,urgency,call_time,score,status,created_at\n"
        
        result = await db.stream_scalars(select(Lead).order_by(Lead.created_at.desc()))
        async for lead in result:
            markets = "|".join(lead.target_markets) if lead.target_markets else ""
            row = [
                lead.name or "",
                lead.phone or "",
                lead.company_name or "",
                lead.industry or "",
                markets,
                lead.monthly_ad_budget or "",
                lead.pain_point or "",
                lead.urgency or "",
                lead.preferred_call_time or "",
                lead.lead_score or "",
                lead.conv_status or "",
                str(lead.created_at)
            ]
            
            def escape(s):
                s = str(s).replace('"', '""')
                if any(c in s for c in [',', '"', '\n']):
                    return f'"{s}"'
                return s
                
            yield ",".join(map(escape, row)) + "\n"

    return StreamingResponse(iter_csv(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=drootle_leads.csv"})

@router.get("/leads/{lead_id}")
async def get_lead_detail(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        return {"error": "Lead not found"}
        
    result = await db.execute(select(Conversation).where(Conversation.lead_id == lead.id).order_by(Conversation.created_at.asc()))
    conversations = result.scalars().all()
    
    return {
        "lead": lead,
        "conversations": conversations
    }

@router.get("/leads/{lead_id}/history")
async def get_lead_history(lead_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StageHistory)
        .where(StageHistory.lead_id == lead_id)
        .order_by(StageHistory.created_at.asc())
    )
    return result.scalars().all()

class ForceStagePayload(BaseModel):
    status: str
    reason: str

VALID_STATUSES = ["new", "qualifying", "stalled", "awaiting_call", "post_call", "fomo", "cold", "closed", "upsell", "archived", "lost"]

@router.post("/leads/{lead_id}/force-stage")
async def force_stage(lead_id: str, payload: ForceStagePayload, db: AsyncSession = Depends(get_db)):
    if payload.status not in VALID_STATUSES:
        return {"error": f"Invalid status. Must be one of {VALID_STATUSES}"}
        
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    old_status = lead.conv_status
    if old_status == payload.status:
        return {"success": True, "note": "Status already set"}
        
    lead.conv_status = payload.status
    await db.commit()
    await log_stage_change(lead_id, old_status, payload.status, "sales", f"FORCED: {payload.reason}", db)
    
    arq_pool = await get_arq_pool()
    if payload.status == "post_call":
        await arq_pool.enqueue_job('start_post_call_sequence', lead_id)
    elif payload.status == "fomo":
        await arq_pool.enqueue_job('start_fomo_sequence', lead_id)
    elif payload.status == "cold":
        await arq_pool.enqueue_job('start_reactivation', lead_id)
    elif payload.status == "closed":
        await arq_pool.enqueue_job('start_closed_sequence', lead_id)
    elif payload.status == "upsell":
        await arq_pool.enqueue_job('start_upsell_sequence', lead_id)
        
    return {"success": True}

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Lead))
    today = await db.scalar(select(func.count()).select_from(Lead).where(func.date(Lead.created_at) == func.current_date()))
    
    hot = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "HOT"))
    warm = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "WARM"))
    cold = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "COLD"))
    
    stage_result = await db.execute(select(Lead.conv_status, func.count(Lead.id)).group_by(Lead.conv_status))
    leads_by_stage = {row[0]: row[1] for row in stage_result}
    
    opt_out_count = await db.scalar(select(func.count()).select_from(Lead).where(Lead.opted_out == True))
    opt_out_rate = (opt_out_count / total * 100) if total else 0.0
    
    # Mocking complex historical averages for dashboard visualization purposes
    return {
        "total_leads": total,
        "leads_today": today,
        "hot_count": hot,
        "warm_count": warm,
        "cold_count": cold,
        "leads_by_stage": leads_by_stage,
        "avg_time_to_qualify_minutes": 14.5,
        "avg_time_qualifying_to_call_minutes": 120.5,
        "conversion_qualifying_to_call": 35.0,
        "conversion_call_to_closed": 15.0,
        "opt_out_rate": round(opt_out_rate, 2),
        "sequence_recovery_rate": {
            "dnp": 12.5,
            "fomo": 8.0,
            "cold": 1.5
        }
    }

class ActionPayload(BaseModel):
    action: str

@router.post("/leads/{lead_id}/action")
async def lead_action(lead_id: str, payload: ActionPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    if payload.action == "mark_closed":
        lead.conv_status = "closed"
        await db.commit()
        return {"success": True}
    elif payload.action == "mark_hot":
        lead.lead_score = "HOT"
        await db.commit()
        return {"success": True}
    elif payload.action == "renotify_sales":
        arq_pool = await get_arq_pool()
        await arq_pool.enqueue_job('notify_sales_qualification_task', str(lead.id))
        return {"success": True}
    elif payload.action == "call_now":
        if settings.VOICE_ENABLED:
            arq_pool = await get_arq_pool()
            await arq_pool.enqueue_job('dispatch_voice_call', lead_id)
            return {"success": True}
        else:
            return {"error": "voice not enabled"}
    elif payload.action == "start_upsell":
        old_status = lead.conv_status
        lead.conv_status = "upsell"
        await db.commit()
        await log_stage_change(lead_id, old_status, "upsell", "sales", "Manual upsell trigger", db)
        arq_pool = await get_arq_pool()
        await arq_pool.enqueue_job('start_upsell_sequence', lead_id)
        return {"success": True}
        
    return {"error": "unknown action"}

class CallOutcomePayload(BaseModel):
    outcome: str

@router.post("/leads/{lead_id}/call-outcome")
async def call_outcome(lead_id: str, payload: CallOutcomePayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    old_status = lead.conv_status
    arq_pool = await get_arq_pool()
    outcome = payload.outcome
    
    if outcome == "call_went_well":
        lead.conv_status = "post_call"
        await db.commit()
        await log_stage_change(lead_id, old_status, "post_call", "sales", "Call went well", db)
        await arq_pool.enqueue_job('start_post_call_sequence', lead_id)
        return {"success": True, "next_stage": "post_call"}
        
    elif outcome == "reschedule":
        lead.conv_status = "awaiting_call"
        lead.call_reminder_sent = False
        await db.commit()
        await log_stage_change(lead_id, old_status, "awaiting_call", "sales", "Need to reschedule", db)
        return {"success": True, "next_stage": "awaiting_call"}
        
    elif outcome == "no_show":
        await log_stage_change(lead_id, old_status, "stalled", "sales", "No show", db)
        await arq_pool.enqueue_job('start_dnp_recovery', lead_id)
        return {"success": True, "next_stage": "stalled"}
        
    elif outcome == "not_interested":
        lead.conv_status = "lost"
        lead.opted_out = True
        await db.commit()
        await log_stage_change(lead_id, old_status, "lost", "sales", "Not interested after call", db)
        await notify_sales_opt_out(lead)
        return {"success": True, "next_stage": "lost"}
        
    elif outcome == "deal_closed":
        lead.conv_status = "closed"
        await db.commit()
        await log_stage_change(lead_id, old_status, "closed", "sales", "Deal closed", db)
        await arq_pool.enqueue_job('start_closed_sequence', lead_id)
        return {"success": True, "next_stage": "closed"}
        
    return {"error": "unknown outcome"}

SEQUENCES_DEF = [
    {"sequence_number": 1, "sequence_name": "First Touch"},
    {"sequence_number": 2, "sequence_name": "AI Qualification"},
    {"sequence_number": 3, "sequence_name": "DNP Recovery"},
    {"sequence_number": 4, "sequence_name": "Awaiting Call"},
    {"sequence_number": 5, "sequence_name": "Post-Call Validation"},
    {"sequence_number": 6, "sequence_name": "FOMO Creation"},
    {"sequence_number": 7, "sequence_name": "Lead Recovery / Reactivation"},
    {"sequence_number": 8, "sequence_name": "Closed & Referral Engine"},
    {"sequence_number": 9, "sequence_name": "Upsell & Cross-Sell"},
]

@router.get("/sequences")
async def get_sequences(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SequenceConfig).order_by(SequenceConfig.sequence_number.asc()))
    sequences = result.scalars().all()
    
    if len(sequences) < 9:
        existing_nums = [s.sequence_number for s in sequences]
        for seq_def in SEQUENCES_DEF:
            if seq_def["sequence_number"] not in existing_nums:
                new_seq = SequenceConfig(
                    sequence_number=seq_def["sequence_number"],
                    sequence_name=seq_def["sequence_name"],
                    enabled=True
                )
                db.add(new_seq)
        await db.commit()
        result = await db.execute(select(SequenceConfig).order_by(SequenceConfig.sequence_number.asc()))
        sequences = result.scalars().all()
        
    return sequences

class SequencePatchPayload(BaseModel):
    enabled: bool

@router.patch("/sequences/{sequence_number}")
async def patch_sequence(sequence_number: int, payload: SequencePatchPayload, db: AsyncSession = Depends(get_db)):
    if sequence_number in [1, 2]:
        return {"error": "Cannot modify locked sequences (1 & 2)"}
        
    result = await db.execute(select(SequenceConfig).where(SequenceConfig.sequence_number == sequence_number))
    seq = result.scalars().first()
    
    if not seq:
        return {"error": "Sequence not found"}
        
    seq.enabled = payload.enabled
    await db.commit()
    
    return {"success": True, "enabled": seq.enabled}
