import pytest
from uuid import uuid4
from datetime import date

from bank.bank import Bank
from bank.security_config import SecurityConfig
from client.client import Client
from enums.enums import ClientStatus, SuspiciousEventType
from exceptions.exceptions import (
    AuthenticationError,
    ClientBlockedError,
)


# ---------------------------------------------------------------------------
# security_config
# ---------------------------------------------------------------------------

def test_bank_uses_default_security_config(bank):
    assert bank.security_config == SecurityConfig()


def test_default_config_has_expected_values():
    assert SecurityConfig().max_login_attempts == 3
    assert SecurityConfig().night_start_hour == 0
    assert SecurityConfig().night_end_hour == 5
    assert SecurityConfig().rapid_account_opening_threshold == 3
    assert SecurityConfig().suspicious_frequency_threshold == 10
    assert SecurityConfig().suspicious_actions_max == 10_000


def test_config_is_frozen():
    """frozen=True — конфиг нельзя случайно изменить после создания."""
    config = SecurityConfig()
    with pytest.raises(Exception):        # FrozenInstanceError
        config.max_login_attempts = 99


# ---------------------------------------------------------------------------
# _log_suspicious_action
# ---------------------------------------------------------------------------

def test_log_suspicious_action_creates_and_stores(bank, registered_client):
    action = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN,
        client_id=registered_client.id,
    )

    assert action in bank._suspicious_actions
    assert action.event_type == SuspiciousEventType.FAILED_LOGIN
    assert action.client_id == registered_client.id
    assert action.account_id is None
    assert action.details == {}
    assert action.resolved is False
    assert action.id is not None
    assert action.timestamp is not None


def test_log_suspicious_action_defaults(bank):
    action = bank._log_suspicious_action(SuspiciousEventType.FAILED_LOGIN)

    assert action.client_id is None
    assert action.account_id is None
    assert action.details == {}


def test_log_suspicious_action_preserves_details(bank, registered_client):
    details = {"attempt": 1, "reason": "wrong_pin"}
    action = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN,
        client_id=registered_client.id,
        details=details,
    )
    assert action.details == details


def test_log_suspicious_action_unique_ids(bank, registered_client):
    a1 = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN, client_id=registered_client.id
    )
    a2 = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN, client_id=registered_client.id
    )
    assert a1.id != a2.id


# ---------------------------------------------------------------------------
# authenticate_client — успех
# ---------------------------------------------------------------------------

def test_authenticate_success_returns_true(bank, registered_client):
    assert bank.authenticate_client(registered_client.id, "1234") is True


def test_authenticate_success_resets_counter(bank, registered_client):
    # две неудачи — счётчик = 2
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")
    assert bank._login_attempts[registered_client.id] == 2

    assert bank.authenticate_client(registered_client.id, "1234") is True
    assert bank._login_attempts[registered_client.id] == 0


def test_authenticate_success_does_not_log_events(bank, registered_client):
    bank.authenticate_client(registered_client.id, "1234")
    assert bank._suspicious_actions == []


# ---------------------------------------------------------------------------
# authenticate_client — валидация аргументов
# ---------------------------------------------------------------------------

def test_authenticate_invalid_client_id_type(bank):
    with pytest.raises(AuthenticationError, match="Некорректный ID"):
        bank.authenticate_client("not-a-uuid", "1234")


def test_authenticate_invalid_pin_type(bank, registered_client):
    with pytest.raises(AuthenticationError, match="PIN"):
        bank.authenticate_client(registered_client.id, 1234)


def test_authenticate_client_not_found(bank):
    with pytest.raises(AuthenticationError, match="не найден"):
        bank.authenticate_client(uuid4(), "1234")


def test_authenticate_blocked_client_rejected(bank, registered_client):
    registered_client.status = ClientStatus.BLOCKED
    with pytest.raises(AuthenticationError, match="не активен"):
        bank.authenticate_client(registered_client.id, "1234")


# ---------------------------------------------------------------------------
# authenticate_client — неверный PIN и блокировка
# ---------------------------------------------------------------------------

def test_authenticate_wrong_pin_increments_counter(bank, registered_client):
    with pytest.raises(AuthenticationError):
        bank.authenticate_client(registered_client.id, "0000")
    assert bank._login_attempts[registered_client.id] == 1


def test_authenticate_wrong_pin_reports_remaining(bank, registered_client):
    with pytest.raises(AuthenticationError, match="Осталось попыток: 2"):
        bank.authenticate_client(registered_client.id, "0000")


def test_authenticate_remaining_decreases(bank, registered_client):
    with pytest.raises(AuthenticationError, match="Осталось попыток: 2"):
        bank.authenticate_client(registered_client.id, "0000")
    with pytest.raises(AuthenticationError, match="Осталось попыток: 1"):
        bank.authenticate_client(registered_client.id, "0000")


def test_authenticate_blocks_after_max_attempts(bank, registered_client):
    max_attempts = bank.security_config.max_login_attempts

    for _ in range(max_attempts - 1):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")

    with pytest.raises(ClientBlockedError):
        bank.authenticate_client(registered_client.id, "0000")

    assert registered_client.status == ClientStatus.BLOCKED


def test_authenticate_blocked_cannot_retry_with_correct_pin(bank, registered_client):
    max_attempts = bank.security_config.max_login_attempts
    for _ in range(max_attempts):
        with pytest.raises((AuthenticationError, ClientBlockedError)):
            bank.authenticate_client(registered_client.id, "0000")

    # Даже с правильным PIN — отказ
    with pytest.raises(AuthenticationError, match="не активен"):
        bank.authenticate_client(registered_client.id, "1234")


# ---------------------------------------------------------------------------
# authenticate_client — логирование событий
# ---------------------------------------------------------------------------

def test_authenticate_logs_failed_login(bank, registered_client):
    with pytest.raises(AuthenticationError):
        bank.authenticate_client(registered_client.id, "0000")

    failed = [
        a for a in bank._suspicious_actions
        if a.event_type == SuspiciousEventType.FAILED_LOGIN
    ]
    assert len(failed) == 1
    assert failed[0].client_id == registered_client.id
    assert failed[0].details == {"attempt": 1}


def test_authenticate_logs_each_failed_attempt(bank, registered_client):
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")

    failed = [
        a for a in bank._suspicious_actions
        if a.event_type == SuspiciousEventType.FAILED_LOGIN
    ]
    assert len(failed) == 2
    assert [a.details["attempt"] for a in failed] == [1, 2]


def test_authenticate_logs_client_blocked(bank, registered_client):
    max_attempts = bank.security_config.max_login_attempts
    for _ in range(max_attempts):
        with pytest.raises((AuthenticationError, ClientBlockedError)):
            bank.authenticate_client(registered_client.id, "0000")

    blocked = [
        a for a in bank._suspicious_actions
        if a.event_type == SuspiciousEventType.CLIENT_BLOCKED
    ]
    assert len(blocked) == 1
    assert blocked[0].client_id == registered_client.id
    assert blocked[0].details == {"attempts_total": max_attempts}


def test_authenticate_total_event_count_after_block(bank, registered_client):
    max_attempts = bank.security_config.max_login_attempts
    for _ in range(max_attempts):
        with pytest.raises((AuthenticationError, ClientBlockedError)):
            bank.authenticate_client(registered_client.id, "0000")

    # N неудач + 1 блокировка
    assert len(bank._suspicious_actions) == max_attempts + 1


# ---------------------------------------------------------------------------
# Мультиклиентность — изоляция счётчиков
# ---------------------------------------------------------------------------

def test_authenticate_attempts_isolated_per_client(bank, client):
    bank.add_client(client)

    other = Client(
        name="Пётр Петров",
        birth_date=date(1985, 5, 5),
        phone="+79990002233",
        email="petr@example.com",
        pin_code="5678",
    )
    bank.add_client(other)

    # клиент 1 ошибается один раз
    with pytest.raises(AuthenticationError):
        bank.authenticate_client(client.id, "0000")

    # клиент 2 входит успешно — его счётчик не затронут
    assert bank.authenticate_client(other.id, "5678") is True
    assert bank._login_attempts[client.id] == 1
    assert bank._login_attempts[other.id] == 0


# ---------------------------------------------------------------------------
# Кастомный конфиг
# ---------------------------------------------------------------------------

def test_custom_config_max_attempts_respected(bank, registered_client):
    """
    Bank сейчас принимает только name и жёстко ставит DEFAULT_SECURITY_CONFIG.
    Чтобы протестировать кастом, подменяем приватное поле напрямую.

    Когда конструктор станет принимать config — заменить на:
        bank = Bank("...", SecurityConfig(max_login_attempts=5))
    """
    bank._security_config = SecurityConfig(max_login_attempts=5)

    for _ in range(4):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")
    assert registered_client.status == ClientStatus.ACTIVE

    with pytest.raises(ClientBlockedError):
        bank.authenticate_client(registered_client.id, "0000")
    assert registered_client.status == ClientStatus.BLOCKED