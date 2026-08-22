"""add price data source

Revision ID: 20260822_0002
Revises: 20260822_0001
Create Date: 2026-08-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260822_0002"
down_revision: Union[str, None] = "20260822_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "price_history",
        sa.Column("data_source", sa.String(length=50), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("price_history", "data_source")
