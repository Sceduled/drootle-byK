"""
SQLAlchemy ORM models definition.
"""
import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index, text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(Text, nullable=False, unique=True, index=True)
    password_hash = Column(Text, nullable=False)
    role = Column(Text, default="sales_rep", nullable=False) # 'admin' or 'sales_rep'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=True)
    phone = Column(Text, nullable=False, unique=True, index=True)
    email = Column(Text, nullable=True)
    company_name = Column(Text, nullable=True)

    # Qualification fields
    industry = Column(Text, nullable=True)
    target_markets = Column(ARRAY(Text), nullable=True)
    monthly_ad_budget = Column(Text, nullable=True)
    ads_experience = Column(Text, nullable=True)
    pain_point = Column(Text, nullable=True)
    urgency = Column(Text, nullable=True)
    preferred_call_time = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)

    # Scoring & status
    lead_score = Column(Text, nullable=True, index=True)
    conv_status = Column(Text, default="new", index=True)

    # Source tracking
    source_ad = Column(Text, nullable=True)
    sheet_row_index = Column(Integer, nullable=True)
    assigned_to = Column(Text, index=True, nullable=True)
    project_key = Column(Text, nullable=True, index=True)
    needs_project_assignment = Column(Boolean, default=False, nullable=False)

    # Reminders
    call_booked_at = Column(DateTime(timezone=True), nullable=True)
    call_reminder_sent = Column(Boolean, default=False)

    # Voice & Calls
    last_call_at = Column(DateTime(timezone=True), nullable=True)
    call_count = Column(Integer, default=0)
    call_notes = Column(Text, nullable=True)
    call_attempted = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    call_attempted_at = Column(DateTime(timezone=True), nullable=True)
    call_outcome = Column(Text, nullable=True)
    call_qualified = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    call_partial_data = Column(JSONB, nullable=True)
    call_duration_seconds = Column(Integer, nullable=True)

    # Lifecycle & Sequences
    opted_out = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    escalated = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    current_sequence = Column(Integer, default=0)
    sequence_step = Column(Integer, default=0)
    last_sequence_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    last_inbound_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    conversations = relationship("Conversation", back_populates="lead", cascade="all, delete-orphan")
    notifications = relationship("NotificationLog", back_populates="lead", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="conversations")

    __table_args__ = (
        Index("ix_conversations_lead_id_created_at_desc", "lead_id", text("created_at DESC")),
    )


class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    type = Column(Text, nullable=False)
    recipient = Column(Text, nullable=False)
    message_preview = Column(Text, nullable=True)
    status = Column(Text, default="sent")
    sequence_step = Column(Text, nullable=True)
    replied = Column(Boolean, default=False, server_default=text("false"))
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead", back_populates="notifications")

class StageHistory(Base):
    __tablename__ = "stage_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=False)
    from_status = Column(Text, nullable=True)
    to_status = Column(Text, nullable=False)
    triggered_by = Column(Text, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    lead = relationship("Lead")

    __table_args__ = (
        Index("ix_stage_history_lead_id_created_at_desc", "lead_id", text("created_at DESC")),
    )

class SequenceConfig(Base):
    __tablename__ = "sequence_config"

    id = Column(Integer, primary_key=True, index=True)
    sequence_number = Column(Integer, unique=True, index=True)
    sequence_name = Column(String)
    enabled = Column(Boolean, default=True)


class SequenceTiming(Base):
    __tablename__ = "sequence_timing"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_number = Column(Integer, nullable=False, index=True)
    message_key = Column(Text, nullable=False)
    delay_value = Column(Integer, nullable=False)
    delay_unit = Column(Text, nullable=False)   # "hours" or "days"
    display_order = Column(Integer, nullable=False, server_default=text("0"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    lead_score = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("SimulationMessage", back_populates="session", cascade="all, delete-orphan")


class SimulationMessage(Base):
    __tablename__ = "simulation_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("simulation_sessions.id"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("SimulationSession", back_populates="messages")

    __table_args__ = (
        Index("ix_sim_messages_session_id_created_at_desc", "session_id", text("created_at DESC")),
    )

class CampaignContext(Base):
    __tablename__ = "campaign_context"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_key = Column(Text, ForeignKey("projects.project_key"), nullable=True, index=True)
    context_key = Column(String(100), nullable=False)
    context_value = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('project_key', 'context_key', name='uq_project_context'),
    )

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_key = Column(Text, nullable=False, unique=True, index=True)
    project_name = Column(Text, nullable=False)
    area = Column(Text, nullable=False)
    property_type = Column(Text, nullable=False)
    bhk_or_size = Column(Text, nullable=False)
    price_range = Column(Text, nullable=False)
    key_features = Column(Text, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
