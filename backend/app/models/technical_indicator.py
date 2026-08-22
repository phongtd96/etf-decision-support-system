from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.etf import Etf


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    __table_args__ = (
        UniqueConstraint("etf_id", "date", name="uq_technical_indicators_etf_id_date"),
        Index("ix_technical_indicators_etf_id_date", "etf_id", "date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    etf_id: Mapped[int] = mapped_column(ForeignKey("etfs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    sma_20: Mapped[Decimal | None] = mapped_column(Numeric)
    sma_50: Mapped[Decimal | None] = mapped_column(Numeric)
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric)
    macd: Mapped[Decimal | None] = mapped_column(Numeric)
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric)
    volatility_20: Mapped[Decimal | None] = mapped_column(Numeric)

    etf: Mapped["Etf"] = relationship(back_populates="technical_indicators")
