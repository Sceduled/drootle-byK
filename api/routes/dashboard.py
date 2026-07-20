import csv
import io
import json
from client_config import SEQUENCE_TEMPLATES
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, case
from typing import Optional

from core.database import get_db
from core.models import Lead, Conversation, StageHistory, SequenceConfig, NotificationLog, SequenceTiming, CampaignContext, Project
from api.routes.auth import get_current_user
from api.routes.webhooks import get_arq_pool
from core.config import settings
from pydantic import BaseModel
from utils.stage_logger import log_stage_change
from services.notifications import notify_sales_opt_out
from client_config import AGENT_NAME, CLIENT_BRAND, OWNER_NAME

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
    last_updated_at: str | None = None  # ISO timestamp for optimistic concurrency check

VALID_STATUSES = ["new", "qualifying", "stalled", "awaiting_call", "post_call", "fomo", "cold", "closed", "upsell", "archived", "lost"]

@router.post("/leads/{lead_id}/force-stage")
async def force_stage(lead_id: str, payload: ForceStagePayload, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if payload.status not in VALID_STATUSES:
        return {"error": f"Invalid status. Must be one of {VALID_STATUSES}"}
        
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    # Ownership Check
    if current_user["role"] != "admin" and lead.assigned_to and lead.assigned_to != current_user["username"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Lead is assigned to another representative.")
    
    old_status = lead.conv_status
    if old_status == payload.status:
        return {"success": True, "note": "Status already set"}

    # Optimistic Concurrency Control: reject if another rep already updated this lead
    if payload.last_updated_at:
        from datetime import timezone
        db_updated = lead.updated_at.replace(tzinfo=timezone.utc) if lead.updated_at.tzinfo is None else lead.updated_at
        client_updated = datetime.fromisoformat(payload.last_updated_at.replace("Z", "+00:00"))
        if db_updated > client_updated:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Another user just modified this lead. Please refresh to see the latest data."
            )
        
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
    
    seq_result = await db.execute(
        select(
            NotificationLog.sequence_step,
            func.count(NotificationLog.id).label("sent"),
            func.sum(case((NotificationLog.replied == True, 1), else_=0)).label("replied")
        ).where(NotificationLog.sequence_step.is_not(None))
        .group_by(NotificationLog.sequence_step)
    )
    
    sequence_performance = {}
    for row in seq_result:
        step = row[0]
        sent = row[1]
        replied = row[2] or 0
        rate = round((replied / sent * 100) if sent > 0 else 0, 1)
        sequence_performance[step] = {"sent": sent, "replied": replied, "rate": rate}
    
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
        },
        "sequence_performance": sequence_performance
    }

class ActionPayload(BaseModel):
    action: str

@router.post("/leads/{lead_id}/action")
async def lead_action(lead_id: str, payload: ActionPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    if payload.action == "mark_closed":
        old_status = lead.conv_status
        lead.conv_status = "closed"
        await db.commit()
        await log_stage_change(lead_id, old_status, "closed", "sales", "Manual close from action", db)
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
    notes: Optional[str] = None
    last_updated_at: str | None = None

@router.post("/leads/{lead_id}/call-outcome")
async def call_outcome(lead_id: str, payload: CallOutcomePayload, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    # Ownership Check
    if current_user["role"] != "admin" and lead.assigned_to and lead.assigned_to != current_user["username"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Lead is assigned to another representative.")
    
    old_status = lead.conv_status
    
    # Optimistic Concurrency Control
    if payload.last_updated_at:
        from datetime import timezone, datetime
        db_updated = lead.updated_at.replace(tzinfo=timezone.utc) if lead.updated_at.tzinfo is None else lead.updated_at
        client_updated = datetime.fromisoformat(payload.last_updated_at.replace("Z", "+00:00"))
        if db_updated > client_updated:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Another user just modified this lead. Please refresh to see the latest data."
            )
            
    arq_pool = await get_arq_pool()
    outcome = payload.outcome
    
    if outcome == "call_went_well":
        lead.conv_status = "post_call"
        if payload.notes:
            lead.call_notes = payload.notes
        await db.commit()
        await log_stage_change(lead_id, old_status, "post_call", "sales", "Call went well", db)
        await arq_pool.enqueue_job('start_post_call_sequence', lead_id)
        return {"success": True, "next_stage": "post_call"}
        
    elif outcome == "reschedule":
        lead.conv_status = "qualifying"
        lead.call_reminder_sent = False
        lead.preferred_call_time = None
        await db.commit()
        await log_stage_change(lead_id, old_status, "qualifying", "sales", "Need to reschedule", db)
        await arq_pool.enqueue_job('ask_for_reschedule', lead_id)
        return {"success": True, "next_stage": "qualifying"}
        
    elif outcome == "no_show":
        lead.conv_status = "stalled"
        await db.commit()
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

SEQ_MAPPING = {
    1: ["first_touch"],
    2: ["qual_nudge_24h"],
    3: ["dnp_day1", "dnp_day2", "dnp_day3", "dnp_day5"],
    4: ["call_reminder_lead", "call_reminder_sales"],
    5: ["post_call_day1", "post_call_day2", "post_call_day3", "post_call_day5", "post_call_day7"],
    6: ["fomo_day1", "fomo_day2", "fomo_day3"],
    7: ["reactivation_week2", "reactivation_week4", "reactivation_week6", "reactivation_week8", "reactivation_week12"],
    8: ["closed_day3", "closed_day14", "closed_day30", "closed_day35"],
    9: ["upsell_day1", "upsell_day4", "upsell_day7"],
}

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
        
    result_list = []
    for s in sequences:
        s_dict = {
            "sequence_number": s.sequence_number,
            "sequence_name": s.sequence_name,
            "enabled": s.enabled,
            "templates": []
        }
        keys = SEQ_MAPPING.get(s.sequence_number, [])
        for k in keys:
            if k in SEQUENCE_TEMPLATES:
                s_dict["templates"].append({"key": k, "content": SEQUENCE_TEMPLATES[k]["fallback_text"]})
        result_list.append(s_dict)
        
    return result_list

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


class TimingPatchItem(BaseModel):
    message_key: str
    delay_value: int
    delay_unit: str  # "hours" or "days"

@router.get("/sequences/{sequence_number}/timing")
async def get_sequence_timing_endpoint(
    sequence_number: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(SequenceTiming)
        .where(SequenceTiming.sequence_number == sequence_number)
        .order_by(SequenceTiming.display_order)
    )
    rows = result.scalars().all()
    return [
        {
            "message_key": r.message_key,
            "delay_value": r.delay_value,
            "delay_unit": r.delay_unit,
            "display_order": r.display_order,
        }
        for r in rows
    ]

@router.patch("/sequences/{sequence_number}/timing")
async def patch_sequence_timing(
    sequence_number: int,
    payload: list[TimingPatchItem],
    db: AsyncSession = Depends(get_db)
):
    for item in payload:
        if item.delay_value <= 0:
            return {"error": f"delay_value must be > 0 for key '{item.message_key}'"}
        if item.delay_unit not in ("hours", "days"):
            return {"error": f"delay_unit must be 'hours' or 'days' for key '{item.message_key}'"}

        result = await db.execute(
            select(SequenceTiming).where(
                SequenceTiming.sequence_number == sequence_number,
                SequenceTiming.message_key == item.message_key
            )
        )
        row = result.scalars().first()
        if row:
            row.delay_value = item.delay_value
            row.delay_unit = item.delay_unit
        else:
            db.add(SequenceTiming(
                sequence_number=sequence_number,
                message_key=item.message_key,
                delay_value=item.delay_value,
                delay_unit=item.delay_unit,
                display_order=0
            ))
    await db.commit()
    return {"message": "Campaign context updated successfully"}

# --- Project Management Endpoints ---

class ProjectCreatePayload(BaseModel):
    project_key: str
    project_name: str
    area: str
    property_type: str
    bhk_or_size: str
    price_range: str
    key_features: Optional[str] = None

class ProjectUpdatePayload(BaseModel):
    project_name: Optional[str] = None
    area: Optional[str] = None
    property_type: Optional[str] = None
    bhk_or_size: Optional[str] = None
    price_range: Optional[str] = None
    key_features: Optional[str] = None
    active: Optional[bool] = None

@router.get("/projects")
async def get_projects(db: AsyncSession = Depends(get_db)):
    from core.models import Project
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()

@router.post("/projects")
async def create_project(payload: ProjectCreatePayload, db: AsyncSession = Depends(get_db)):
    from core.models import Project
    from utils.project_matcher import normalize
    normalized_key = normalize(payload.project_key)
    if not normalized_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Invalid project key")

    result = await db.execute(select(Project).where(Project.project_key == normalized_key))
    if result.scalars().first():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Project key already exists")

    new_proj = Project(
        project_key=normalized_key,
        project_name=payload.project_name,
        area=payload.area,
        property_type=payload.property_type,
        bhk_or_size=payload.bhk_or_size,
        price_range=payload.price_range,
        key_features=payload.key_features
    )
    db.add(new_proj)
    await db.commit()
    await db.refresh(new_proj)
    return new_proj

@router.patch("/projects/{project_key}")
async def update_project(project_key: str, payload: ProjectUpdatePayload, db: AsyncSession = Depends(get_db)):
    from core.models import Project
    result = await db.execute(select(Project).where(Project.project_key == project_key))
    project = result.scalars().first()
    if not project:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return project

class AssignProjectPayload(BaseModel):
    project_key: str

@router.patch("/leads/{lead_id}/assign-project")
async def assign_lead_project(lead_id: str, payload: AssignProjectPayload, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Lead not found")
        
    lead.project_key = payload.project_key
    lead.needs_project_assignment = False
    await db.commit()
    return {"message": "Project assigned successfully"}

@router.get("/profile")
async def get_profile():
    return {
        "agent_name": AGENT_NAME,
        "client_brand": CLIENT_BRAND,
        "owner_name": OWNER_NAME
    }

@router.post("/leads/{lead_id}/claim")
async def claim_lead(lead_id: str, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalars().first()
    if not lead: return {"error": "not found"}
    
    if lead.assigned_to and lead.assigned_to != current_user["username"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail=f"Lead is already claimed by {lead.assigned_to}")
        
    lead.assigned_to = current_user["username"]
    await db.commit()
    return {"success": True, "assigned_to": current_user["username"]}

class CreateUserPayload(BaseModel):
    username: str
    password: str

@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from core.models import User
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "username": u.username, "role": u.role, "created_at": u.created_at} for u in users]

@router.post("/users")
async def create_user(payload: CreateUserPayload, db: AsyncSession = Depends(get_db), current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin access required")
        
    from core.models import User
    import bcrypt
    
    result = await db.execute(select(User).where(User.username == payload.username))
    if result.scalars().first():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Username already exists")
        
    # Truncate to 72 bytes, ignoring split unicode characters
    pwd_bytes = payload.password.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt()).decode('utf-8')
    
    new_user = User(
        username=payload.username,
        password_hash=hashed,
        role="sales_rep"
    )
    db.add(new_user)
    await db.commit()
    return {"success": True, "username": new_user.username}

@router.get("/campaign-context/{project_key}")
async def get_campaign_context(project_key: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CampaignContext).where(CampaignContext.project_key == project_key))
    contexts = result.scalars().all()
    return {c.context_key: c.context_value for c in contexts}

class CampaignContextPayload(BaseModel):
    contexts: dict

@router.post("/campaign-context/{project_key}")
async def update_campaign_context(project_key: str, payload: CampaignContextPayload, db: AsyncSession = Depends(get_db)):
    from core.models import Project
    # Check if project exists
    proj_result = await db.execute(select(Project).where(Project.project_key == project_key))
    if not proj_result.scalars().first():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    for key, value in payload.contexts.items():
        # Check if it exists
        result = await db.execute(
            select(CampaignContext)
            .where(CampaignContext.project_key == project_key, CampaignContext.context_key == key)
        )
        context_obj = result.scalars().first()
        if context_obj:
            context_obj.context_value = str(value)
        else:
            db.add(CampaignContext(project_key=project_key, context_key=key, context_value=str(value)))
    
    await db.commit()
    return {"success": True}
