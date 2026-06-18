"""add simulation tables

Revision ID: 20260618_115200
Revises: 20260617_080436
Create Date: 2026-06-18 11:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260618_115200'
down_revision: Union[str, None] = '20260617_080436'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('simulation_sessions',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('simulation_messages',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['session_id'], ['simulation_sessions.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_sim_messages_session_id_created_at_desc', 'simulation_messages', ['session_id', sa.text('created_at DESC')], unique=False)


def downgrade() -> None:
    op.drop_index('ix_sim_messages_session_id_created_at_desc', table_name='simulation_messages')
    op.drop_table('simulation_messages')
    op.drop_table('simulation_sessions')
