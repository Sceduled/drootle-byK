"""add sequence_timing table

Revision ID: 20260619_sequence_timing
Revises: 20260618_123500
Create Date: 2026-06-19 17:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import uuid

revision: str = '20260619_sequence_timing'
down_revision: Union[str, None] = '20260618_123500'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sequence_timing',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('sequence_number', sa.Integer(), nullable=False, index=True),
        sa.Column('message_key', sa.Text(), nullable=False),
        sa.Column('delay_value', sa.Integer(), nullable=False),
        sa.Column('delay_unit', sa.Text(), nullable=False),   # "hours" or "days"
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Seed with current hardcoded values from tasks.py
    seed_rows = [
        # SEQ 3 — DNP Recovery
        (3, 'dnp_message_1',               2,  'hours', 1),
        (3, 'dnp_message_2',              24,  'hours', 2),
        (3, 'dnp_message_3',              48,  'hours', 3),
        (3, 'dnp_message_4',              72,  'hours', 4),
        (3, 'check_dnp_exhausted',        24,  'hours', 5),

        # SEQ 5 — Post-Call
        (5, 'post_call_message_2',         1,  'days',  1),
        (5, 'post_call_message_3',         2,  'days',  2),
        (5, 'post_call_message_4',         4,  'days',  3),
        (5, 'post_call_message_5',         6,  'days',  4),
        (5, 'check_post_call_complete',    7,  'days',  5),

        # SEQ 6 — FOMO
        (6, 'fomo_message_2',              1,  'days',  1),
        (6, 'fomo_message_3',              2,  'days',  2),
        (6, 'check_fomo_complete',         3,  'days',  3),

        # SEQ 7 — Reactivation
        (7, 'reactivation_from_cold',     14,  'days',  0),  # delay before first reactivation fires
        (7, 'reactivation_2',             14,  'days',  1),
        (7, 'reactivation_3',             28,  'days',  2),
        (7, 'reactivation_4',             42,  'days',  3),
        (7, 'reactivation_5',             70,  'days',  4),
        (7, 'check_reactivation_complete', 84, 'days',  5),

        # SEQ 8 — Closed
        (8, 'closed_message_1',            3,  'days',  1),
        (8, 'closed_message_2',           14,  'days',  2),
        (8, 'closed_message_3',           30,  'days',  3),
        (8, 'closed_message_4',           35,  'days',  4),

        # SEQ 9 — Upsell
        (9, 'upsell_message_2',            4,  'days',  1),
        (9, 'upsell_message_3',            7,  'days',  2),
    ]

    rows_sql = ", ".join(
        f"('{uuid.uuid4()}', {seq}, '{key}', {val}, '{unit}', {order})"
        for seq, key, val, unit, order in seed_rows
    )
    op.execute(
        f"INSERT INTO sequence_timing (id, sequence_number, message_key, delay_value, delay_unit, display_order) "
        f"VALUES {rows_sql}"
    )


def downgrade() -> None:
    op.drop_table('sequence_timing')
