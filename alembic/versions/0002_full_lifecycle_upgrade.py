"""full_lifecycle_upgrade

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14 10:14:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. Update leads table
    op.add_column('leads', sa.Column('opted_out', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('leads', sa.Column('escalated', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('leads', sa.Column('current_sequence', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('leads', sa.Column('sequence_step', sa.Integer(), nullable=True, server_default='0'))
    op.add_column('leads', sa.Column('last_sequence_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Create stage_history table
    op.create_table('stage_history',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('lead_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('from_status', sa.Text(), nullable=True),
    sa.Column('to_status', sa.Text(), nullable=False),
    sa.Column('triggered_by', sa.Text(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stage_history_lead_id_created_at_desc', 'stage_history', ['lead_id', sa.text('created_at DESC')], unique=False)

    # 3. Create sequence_config table
    op.create_table('sequence_config',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('sequence_name', sa.Text(), nullable=False),
    sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('sequence_number')
    )

    # 4. Seed sequence_config table
    import uuid
    from datetime import datetime
    now = datetime.utcnow()
    sequences = [
        (str(uuid.uuid4()), 1, 'First Touch', True, now, now),
        (str(uuid.uuid4()), 2, 'AI Qualification', True, now, now),
        (str(uuid.uuid4()), 3, 'DNP Recovery', True, now, now),
        (str(uuid.uuid4()), 4, 'Awaiting Call', True, now, now),
        (str(uuid.uuid4()), 5, 'Post-Call Validation', True, now, now),
        (str(uuid.uuid4()), 6, 'FOMO Creation', True, now, now),
        (str(uuid.uuid4()), 7, 'Lead Recovery', True, now, now),
        (str(uuid.uuid4()), 8, 'Closed / Referral + Review', True, now, now),
        (str(uuid.uuid4()), 9, 'Upsell / Cross-sell', True, now, now)
    ]
    
    values_str = ", ".join(f"('{s[0]}', {s[1]}, '{s[2]}', {s[3]}, '{s[4]}', '{s[5]}')" for s in sequences)
    op.execute(f"INSERT INTO sequence_config (id, sequence_number, sequence_name, enabled, created_at, updated_at) VALUES {values_str}")

def downgrade() -> None:
    op.drop_table('sequence_config')
    op.drop_index('ix_stage_history_lead_id_created_at_desc', table_name='stage_history')
    op.drop_table('stage_history')
    op.drop_column('leads', 'last_sequence_at')
    op.drop_column('leads', 'sequence_step')
    op.drop_column('leads', 'current_sequence')
    op.drop_column('leads', 'escalated')
    op.drop_column('leads', 'opted_out')
