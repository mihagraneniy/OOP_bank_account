import pytest

from bank.bank import Bank
from client.client import Client
from enums.enums import ClientStatus
from exceptions.exceptions import InvalidOperationError

from datetime import date


@pytest.fixture
def bank():
    return Bank("Тестовый банк")


@pytest.fixture
def client():
    return Client(
        name="Иван Иванов",
        birth_date=date(1990, 1, 1),
        phone="+79990001122",
        email="ivan@example.com"
    )


def test_bank_creation():
    bank = Bank("Тестовый банк")

    assert bank.name == "Тестовый банк"
    assert bank._clients == {}
    assert bank._accounts == {}


def test_bank_rejects_empty_name():
    with pytest.raises(InvalidOperationError):
        Bank("")


def test_add_client(bank, client):
    bank.add_client(client)

    assert client.id in bank._clients
    assert bank._clients[client.id] is client


def test_add_duplicate_client_raises(bank, client):
    bank.add_client(client)

    with pytest.raises(InvalidOperationError):
        bank.add_client(client)


def test_add_non_client_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.add_client("Иван")


def test_add_inactive_client_raises(bank, client):
    client.status = ClientStatus.BLOCKED

    with pytest.raises(InvalidOperationError):
        bank.add_client(client)
