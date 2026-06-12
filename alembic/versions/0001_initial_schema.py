"""initial schema

Revision ID: 0001
Revises: 
Create Date: 2026-06-12 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # leads table
    op.create_table('leads',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('phone', sa.Text(), nullable=False),
    sa.Column('email', sa.Text(), nullable=True),
    sa.Column('company_name', sa.Text(), nullable=True),
    sa.Column('industry', sa.Text(), nullable=True),
    sa.Column('target_markets', postgresql.ARRAY(sa.Text()), nullable=True),
    sa.Column('monthly_ad_budget', sa.Text(), nullable=True),
    sa.Column('ads_experience', sa.Text(), nullable=True),
    sa.Column('pain_point', sa.Text(), nullable=True),
    sa.Column('urgency', sa.Text(), nullable=True),
    sa.Column('preferred_call_time', sa.Text(), nullable=True),
    sa.Column('lead_score', sa.Text(), nullable=True),
    sa.Column('conv_status', sa.Text(), nullable=True, server_default='new'),
    sa.Column('source_ad', sa.Text(), nullable=True),
    sa.Column('sheet_row_index', sa.Integer(), nullable=True),
    sa.Column('call_booked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('call_reminder_sent', sa.Boolean(), nullable=True, server_default=sa.text('false')),
    sa.Column('last_call_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('call_count', sa.Integer(), nullable=True, server_default='0'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_conv_status'), 'leads', ['conv_status'], unique=False)
    op.create_index(op.f('ix_leads_lead_score'), 'leads', ['lead_score'], unique=False)
    op.create_index(op.f('ix_leads_phone'), 'leads', ['phone'], unique=True)

    # conversations table
    op.create_table('conversations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lead_id', sa.UUID(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_lead_id_created_at_desc', 'conversations', ['lead_id', sa.text('created_at DESC')], unique=False)

    # notifications_log table
    op.create_table('notifications_log',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('lead_id', sa.UUID(), nullable=False),
    sa.Column('type', sa.Text(), nullable=False),
    sa.Column('recipient', sa.Text(), nullable=False),
    sa.Column('message_preview', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), nullable=True, server_default='sent'),
    sa.Column('sent_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('notifications_log')
    op.drop_index('ix_conversations_lead_id_created_at_desc', table_name='conversations')
    op.drop_table('conversations')
    op.drop_index(op.f('ix_leads_phone'), table_name='leads')
    op.drop_index(op.f('ix_leads_lead_score'), table_name='leads')
    op.drop_index(op.f('ix_leads_conv_status'), table_name='leads')
    op.drop_table('leads')
