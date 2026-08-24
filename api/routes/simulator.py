"""
Simulator routes for testing AI prompts via chat interface.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import List, Dict, Any
import uuid
import io
import csv

from core.database import get_db
from core.models import SimulationSession, SimulationMessage, Lead
from services.gpt import process_message, generate_summary_from_history_text
from client_config import SEQUENCE_TEMPLATES, CLIENT_BRAND

router = APIRouter()

@router.get("/projects")
async def get_projects(db: AsyncSession = Depends(get_db)):
    from core.models import Project
    result = await db.execute(select(Project).order_by(Project.project_name))
    projects = result.scalars().all()
    return [{"project_key": p.project_key, "project_name": p.project_name, "area": p.area} for p in projects]

@router.post("/start")
async def start_simulation(payload: Dict[str, str] = Body(...), db: AsyncSession = Depends(get_db)):
    name = payload.get("name", "Test Lead")
    
    project_key = payload.get("project_key")
    
    session = SimulationSession(name=name)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    from prompts.agent import get_sequence_message
    from core.models import Project
    
    project = None
    if project_key:
        result = await db.execute(select(Project).where(Project.project_key == project_key))
        project = result.scalars().first()
    else:
        # Default simulator to whitefield_flat project if not provided
        result = await db.execute(select(Project).where(Project.project_key == "whitefield_flat"))
        project = result.scalars().first()
        
    proj_name = project.project_name if project else "our properties"
    area = project.area if project else ""
    area_text = f" in {area}" if area else ""
    
    opening_message = f"Hi {name}, Priya here from {CLIENT_BRAND}. I saw you recently showed interest in our project {proj_name}{area_text}. I just need a few details about your requirements. Can I get 2 mins of your time?"
    
    ai_msg = SimulationMessage(
        session_id=session.id,
        role="assistant",
        content=opening_message
    )
    db.add(ai_msg)
    await db.commit()
    
    return {
        "session_id": str(session.id), 
        "message": opening_message,
        "lead_score": session.lead_score,
        "ai_summary": session.ai_summary
    }

@router.get("/history/{session_id}")
async def get_simulation_history(session_id: str, db: AsyncSession = Depends(get_db)):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")
        
    result = await db.execute(
        select(SimulationMessage)
        .where(SimulationMessage.session_id == sid)
        .order_by(SimulationMessage.created_at)
    )
    messages = result.scalars().all()
    
    return [
        {"role": msg.role, "content": msg.content, "created_at": msg.created_at}
        for msg in messages
    ]

@router.post("/chat/{session_id}")
async def send_simulation_message(
    session_id: str, 
    payload: Dict[str, str] = Body(...), 
    db: AsyncSession = Depends(get_db)
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")
        
    session_result = await db.execute(select(SimulationSession).where(SimulationSession.id == sid))
    session = session_result.scalars().first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Simulation session not found")
        
    user_text = payload.get("message", "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
        
    # Add user message
    user_msg = SimulationMessage(
        session_id=sid,
        role="user",
        content=user_text
    )
    db.add(user_msg)
    await db.commit()
    
    # Get history
    history_result = await db.execute(
        select(SimulationMessage)
        .where(SimulationMessage.session_id == sid)
        .order_by(SimulationMessage.created_at)
    )
    history = history_result.scalars().all()
    
    # Create dummy lead for process_message
    dummy_lead = Lead(
        id=uuid.uuid4(),
        name=session.name,
        industry="Simulation",
        conv_status="in_progress",
        project_key="whitefield_flat"
    )
    
    # Call GPT (reusing same logic as normal pipeline)
    reply, extraction = await process_message(
        lead=dummy_lead,
        db=db,
        conversation_history=history[:-1], # pass all except the one we just added? Wait, process_message expects all PREVIOUS messages in conversation_history and takes new_message separately.
        new_message=user_text,
        is_voice=False,
        language_instruction=""
    )
    
    # Save assistant reply
    ai_msg = SimulationMessage(
        session_id=session.id,
        role="assistant",
        content=reply
    )
    db.add(ai_msg)
    await db.commit()

    # Generate summary from history
    result = await db.execute(
        select(SimulationMessage)
        .where(SimulationMessage.session_id == session.id)
        .order_by(SimulationMessage.created_at)
    )
    all_msgs = result.scalars().all()
    history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in all_msgs])
    summary = await generate_summary_from_history_text(history_text)
    
    if summary and summary != "UNABLE_TO_PARSE":
        session.ai_summary = summary
    
    if extraction and "lead_score" in extraction:
        session.lead_score = extraction["lead_score"]

    await db.commit()
    
    return {"reply": reply, "lead_score": session.lead_score, "ai_summary": session.ai_summary}

@router.get("/export")
async def export_simulations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SimulationMessage)
        .options(joinedload(SimulationMessage.session))
        .order_by(SimulationMessage.session_id, SimulationMessage.created_at)
    )
    messages = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session ID", "Simulated Name", "Lead Score", "AI Summary", "Timestamp", "Role", "Message"])
    
    for msg in messages:
        name = msg.session.name if msg.session else "Unknown"
        score = msg.session.lead_score if msg.session else ""
        summary = msg.session.ai_summary if msg.session else ""
        writer.writerow([str(msg.session_id), name, score, summary, msg.created_at.isoformat(), msg.role, msg.content])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=simulation_chats.csv"}
    )

