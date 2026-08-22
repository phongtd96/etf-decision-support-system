from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.prediction import Prediction
    from app.models.price_history import PriceHistory
    from app.models.recommendation import Recommendation
    from app.models.technical_indicator import TechnicalIndicator


class Etf(Base):
    __tablename__ = "etfs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    management_company: Mapped[str | None] = mapped_column(String(255))
    benchmark_index: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="etf")
    technical_indicators: Mapped[list["TechnicalIndicator"]] = relationship(
        back_populates="etf"
    )
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="etf")
    recommendations: Mapped[list["Recommendation"]] = relationship(back_populates="etf")
