from sqlalchemy import String

from app.models.price_history import PriceHistory


def test_price_history_data_source_column() -> None:
    column = PriceHistory.__table__.c.data_source

    assert isinstance(column.type, String)
    assert column.type.length == 50
    assert column.nullable is False
