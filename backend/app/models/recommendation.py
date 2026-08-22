from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.etf import Etf


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index(
            "ix_recommendations_etf_id_recommendation_date",
            "etf_id",
            "recommendation_date",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etfs.id"), nullable=False)
    recommendation_date: Mapped[date] = mapped_column(Date, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(10), nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric)
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric)
    ml_score: Mapped[Decimal | None] = mapped_column(Numeric)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    explanation: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    etf: Mapped["Etf"] = relationship(back_populates="recommendations")
