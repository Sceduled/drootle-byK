"""
SQLAlchemy ORM models definition.
"""
import uuid
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()

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

    # Scoring & status
    lead_score = Column(Text, nullable=True, index=True)
    conv_status = Column(Text, default="new", index=True)

    # Source tracking
    source_ad = Column(Text, nullable=True)
    sheet_row_index = Column(Integer, nullable=True)

    # Reminders
    call_booked_at = Column(DateTime(timezone=True), nullable=True)
    call_reminder_sent = Column(Boolean, default=False)

    # Voice & Calls
    last_call_at = Column(DateTime(timezone=True), nullable=True)
    call_count = Column(Integer, default=0)
    call_notes = Column(Text, nullable=True)

    # Lifecycle & Sequences
    opted_out = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    escalated = Column(Boolean, default=False, nullable=False, server_default=text("false"))
    current_sequence = Column(Integer, default=0)
    sequence_step = Column(Integer, default=0)
    last_sequence_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sequence_number = Column(Integer, unique=True, nullable=False)
    sequence_name = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
