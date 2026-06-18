"""
Simulator routes for testing AI prompts via chat interface.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any
import uuid

from core.database import get_db
from core.models import SimulationSession, SimulationMessage, Lead
from services.gpt import process_message
from client_config import SEQUENCE_MESSAGES

router = APIRouter()

@router.post("/start")
async def start_simulation(payload: Dict[str, str] = Body(...), db: AsyncSession = Depends(get_db)):
    name = payload.get("name", "Test Lead")
    
    session = SimulationSession(name=name)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    opening_message_template = SEQUENCE_MESSAGES.get("first_touch", "Hello {name}!")
    opening_message = opening_message_template.format(name=name)
    
    ai_msg = SimulationMessage(
        session_id=session.id,
        role="assistant",
        content=opening_message
    )
    db.add(ai_msg)
    await db.commit()
    
    return {
        "session_id": str(session.id),
        "name": session.name,
        "message": opening_message
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
        conv_status="in_progress"
    )
    
    # Call GPT (reusing same logic as normal pipeline)
    reply, extraction = await process_message(
        lead=dummy_lead,
        conversation_history=history[:-1], # pass all except the one we just added? Wait, process_message expects all PREVIOUS messages in conversation_history and takes new_message separately.
        new_message=user_text,
        is_voice=False,
        language_instruction=""
    )
    
    # Save assistant reply
    ai_msg = SimulationMessage(
        session_id=sid,
        role="assistant",
        content=reply
    )
    db.add(ai_msg)
    await db.commit()
    
    return {"reply": reply}
