"""create etf analysis tables

Revision ID: 20260822_0001
Revises: 
Create Date: 2026-08-22 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260822_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "etfs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("management_company", sa.String(length=255), nullable=True),
        sa.Column("benchmark_index", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol"),
    )

    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("etf_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(), nullable=True),
        sa.Column("high", sa.Numeric(), nullable=True),
        sa.Column("low", sa.Numeric(), nullable=True),
        sa.Column("close", sa.Numeric(), nullable=True),
        sa.Column("adjusted_close", sa.Numeric(), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["etf_id"], ["etfs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("etf_id", "date", name="uq_price_history_etf_id_date"),
    )
    op.create_index(
        "ix_price_history_etf_id_date",
        "price_history",
        ["etf_id", "date"],
        unique=False,
    )

    op.create_table(
        "technical_indicators",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("etf_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sma_20", sa.Numeric(), nullable=True),
        sa.Column("sma_50", sa.Numeric(), nullable=True),
        sa.Column("rsi_14", sa.Numeric(), nullable=True),
        sa.Column("macd", sa.Numeric(), nullable=True),
        sa.Column("macd_signal", sa.Numeric(), nullable=True),
        sa.Column("volatility_20", sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(["etf_id"], ["etfs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "etf_id",
            "date",
            name="uq_technical_indicators_etf_id_date",
        ),
    )
    op.create_index(
        "ix_technical_indicators_etf_id_date",
        "technical_indicators",
        ["etf_id", "date"],
        unique=False,
    )

    op.create_table(
        "predictions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("etf_id", sa.BigInteger(), nullable=False),
        sa.Column("prediction_date", sa.Date(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("predicted_class", sa.String(length=10), nullable=False),
        sa.Column("probability_up", sa.Numeric(), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("model_version", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["etf_id"], ["etfs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_predictions_etf_id_prediction_date",
        "predictions",
        ["etf_id", "prediction_date"],
        unique=False,
    )

    op.create_table(
        "recommendations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("etf_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_date", sa.Date(), nullable=False),
        sa.Column("recommendation", sa.String(length=10), nullable=False),
        sa.Column("score", sa.Numeric(), nullable=True),
        sa.Column("technical_score", sa.Numeric(), nullable=True),
        sa.Column("ml_score", sa.Numeric(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["etf_id"], ["etfs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recommendations_etf_id_recommendation_date",
        "recommendations",
        ["etf_id", "recommendation_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recommendations_etf_id_recommendation_date",
        table_name="recommendations",
    )
    op.drop_table("recommendations")

    op.drop_index("ix_predictions_etf_id_prediction_date", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index(
        "ix_technical_indicators_etf_id_date",
        table_name="technical_indicators",
    )
    op.drop_table("technical_indicators")

    op.drop_index("ix_price_history_etf_id_date", table_name="price_history")
    op.drop_table("price_history")

    op.drop_table("etfs")
