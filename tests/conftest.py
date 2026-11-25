# tests/conftest.py
import pytest
from datetime import date, timedelta
from uuid import uuid4

from client.client import Client
from enums.enums import ClientStatus


def _born_years_ago(years: int) -> date:
    today = date.today()
    try:
        return today.replace(year=today.year - years)
    except ValueError:  # 29 февраля
        return today.replace(year=today.year - years, day=28)


@pytest.fixture
def make_client():
    """
    Фабрика валидных Client с разумными дефолтами.
    Использование:
        client = make_client()
        client = make_client(name="Пётр", birth_date=...)
    """
    def _factory(**overrides) -> Client:
        defaults = dict(
            status=next(iter(ClientStatus)),
            name="Иван Иванов",
            birth_date=_born_years_ago(30),   # валидный возраст ≥ 18
            phone="+79990001122",
            email="ivan@example.com",
            accounts=[],
        )
        defaults.update(overrides)
        return Client(**defaults)
    return _factory


@pytest.fixture
def client(make_client):
    """Готовый экземпляр — для тестов, где клиент нужен как есть."""
    return make_client()