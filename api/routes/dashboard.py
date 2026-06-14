import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import Optional

from core.database import get_db
from core.models import Lead, Conversation
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
    query = query.order_by(score_sort.asc(), Lead.created_at.desc())
    
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

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    total = await db.scalar(select(func.count()).select_from(Lead))
    today = await db.scalar(select(func.count()).select_from(Lead).where(func.date(Lead.created_at) == func.current_date()))
    week = await db.scalar(select(func.count()).select_from(Lead).where(Lead.created_at >= func.now() - func.interval('7 days')))
    
    hot = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "HOT"))
    warm = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "WARM"))
    cold = await db.scalar(select(func.count()).select_from(Lead).where(Lead.lead_score == "COLD"))
    
    qualified = await db.scalar(select(func.count()).select_from(Lead).where(Lead.conv_status == "qualified"))
    stalled = await db.scalar(select(func.count()).select_from(Lead).where(Lead.conv_status == "stalled"))
    
    ind_result = await db.execute(select(Lead.industry, func.count(Lead.id)).where(Lead.industry.is_not(None)).group_by(Lead.industry))
    industry_counts = {row[0]: row[1] for row in ind_result}
    
    booked = await db.scalar(select(func.count()).select_from(Lead).where(Lead.preferred_call_time.is_not(None)))
    rate = (booked / total * 100) if total else 0.0
    
    avg_minutes = 15.0
    
    return {
        "total_leads": total,
        "leads_today": today,
        "leads_this_week": week,
        "hot_count": hot,
        "warm_count": warm,
        "cold_count": cold,
        "qualified_count": qualified,
        "stalled_count": stalled,
        "by_industry": industry_counts,
        "avg_qualification_minutes": avg_minutes,
        "call_booked_rate": round(rate, 2)
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
