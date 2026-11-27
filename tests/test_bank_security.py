
import pytest
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4
from decimal import Decimal

from bank.bank import Bank
from bank.security_config import SecurityConfig
from enums.enums import (
    AccountStatus,
    AccountType,
    ClientStatus,
    Currency,
    SuspiciousEventType,
)
from exceptions.exceptions import (
    InvalidOperationError,
    AccountNotFoundError,
    AuthenticationError,
    ClientBlockedError,
    OperationTimeError,
    AccountFrozenError,
    AccountClosedError,
)


# ===========================================================================
# Вспомогательные функции
# ===========================================================================

def open_rub_account(bank, client):
    """Открывает дебетовый счёт в RUB."""
    return bank.open_account(
        client,
        AccountType.DEBET,
        Currency.RUB,
    )


def open_account_with_balance(bank, client, amount):
    """Открывает счёт и пополняет его."""
    account = open_rub_account(bank, client)
    account.deposit(Decimal(str(amount)))
    return account


def clock_at(hour, minute=0):
    """Подменяет текущее время для проверки ночного запрета."""
    return patch(
        "bank.bank.datetime",
        **{
            "now.return_value": datetime(2025, 6, 15, hour, minute)
        }
    )


# ===========================================================================
# 1. SecurityConfig
# ===========================================================================

def test_bank_uses_default_security_config(bank):
    assert bank.security_config == SecurityConfig()


def test_default_config_has_expected_values():
    config = SecurityConfig()

    assert config.max_login_attempts == 3
    assert config.night_start_hour == 0
    assert config.night_end_hour == 5
    assert config.rapid_account_opening_threshold == 3
    assert config.suspicious_frequency_threshold == 10
    assert config.suspicious_actions_max == 10_000


def test_config_is_frozen():
    config = SecurityConfig()

    with pytest.raises(Exception):
        config.max_login_attempts = 99


def test_is_night_time_true():
    config = SecurityConfig()

    for hour in (0, 1, 2, 3, 4):
        assert config.is_night_time(
            datetime(2025, 6, 15, hour, 0)
        ) is True


def test_is_night_time_false():
    config = SecurityConfig()

    for hour in (5, 6, 12, 18, 23):
        assert config.is_night_time(
            datetime(2025, 6, 15, hour, 0)
        ) is False


# ===========================================================================
# 2. Журнал подозрительных действий
# ===========================================================================

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
    action = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN
    )

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
    first = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN,
        client_id=registered_client.id,
    )

    second = bank._log_suspicious_action(
        SuspiciousEventType.FAILED_LOGIN,
        client_id=registered_client.id,
    )

    assert first.id != second.id


# ===========================================================================
# 3. Регистрация клиентов
# ===========================================================================

def test_add_client_success(bank, client):
    bank.add_client(client)

    assert client.id in bank.clients
    assert bank.clients[client.id] is client


def test_add_client_invalid_object(bank):
    with pytest.raises(InvalidOperationError):
        bank.add_client("не клиент")


def test_add_client_duplicate(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.add_client(registered_client)


def test_add_inactive_client(bank, make_client):
    inactive_client = make_client(status=ClientStatus.BLOCKED)

    with pytest.raises(InvalidOperationError):
        bank.add_client(inactive_client)


# ===========================================================================
# 4. Открытие счетов
# ===========================================================================

def test_open_account_success(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    assert account.id in bank.accounts
    assert account.id in registered_client.accounts
    assert account.owner is registered_client


def test_open_account_non_client_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.open_account(
            "не клиент",
            AccountType.DEBET,
            Currency.RUB,
        )


def test_open_account_unregistered_client_raises(bank, client):
    with pytest.raises(InvalidOperationError):
        open_rub_account(bank, client)


def test_open_account_invalid_account_type_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(
            registered_client,
            "DEBET",
            Currency.RUB,
        )


def test_open_account_invalid_currency_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(
            registered_client,
            AccountType.DEBET,
            "RUB",
        )


def test_open_account_repeated_calls_create_distinct_accounts(
    bank,
    registered_client,
):
    first = open_rub_account(bank, registered_client)
    second = open_rub_account(bank, registered_client)

    assert first.id != second.id
    assert len(registered_client.accounts) == 2


# ===========================================================================
# 5. Авторизация
# ===========================================================================

def test_authenticate_success_returns_true(bank, registered_client):
    assert bank.authenticate_client(
        registered_client.id,
        "1234",
    ) is True


def test_authenticate_success_resets_counter(bank, registered_client):
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")

    assert bank._login_attempts[registered_client.id] == 2

    assert bank.authenticate_client(
        registered_client.id,
        "1234",
    ) is True

    assert bank._login_attempts[registered_client.id] == 0


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


def test_authenticate_wrong_pin_increments_counter(bank, registered_client):
    with pytest.raises(AuthenticationError):
        bank.authenticate_client(registered_client.id, "0000")

    assert bank._login_attempts[registered_client.id] == 1


def test_authenticate_wrong_pin_reports_remaining(bank, registered_client):
    with pytest.raises(
        AuthenticationError,
        match="Осталось попыток: 2",
    ):
        bank.authenticate_client(registered_client.id, "0000")


def test_authenticate_blocks_after_three_attempts(bank, registered_client):
    for _ in range(2):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")

    with pytest.raises(ClientBlockedError):
        bank.authenticate_client(registered_client.id, "0000")

    assert registered_client.status == ClientStatus.BLOCKED
    assert bank._login_attempts[registered_client.id] == 3


def test_blocked_client_cannot_authenticate_with_correct_pin(
    bank,
    registered_client,
):
    for _ in range(3):
        with pytest.raises((AuthenticationError, ClientBlockedError)):
            bank.authenticate_client(registered_client.id, "0000")

    with pytest.raises(AuthenticationError, match="не активен"):
        bank.authenticate_client(registered_client.id, "1234")


def test_failed_login_is_logged(bank, registered_client):
    with pytest.raises(AuthenticationError):
        bank.authenticate_client(registered_client.id, "0000")

    failed = [
        action
        for action in bank._suspicious_actions
        if action.event_type == SuspiciousEventType.FAILED_LOGIN
    ]

    assert len(failed) == 1
    assert failed[0].client_id == registered_client.id
    assert failed[0].details == {"attempt": 1}


def test_client_blocked_event_is_logged(bank, registered_client):
    for _ in range(3):
        with pytest.raises((AuthenticationError, ClientBlockedError)):
            bank.authenticate_client(registered_client.id, "0000")

    blocked = [
        action
        for action in bank._suspicious_actions
        if action.event_type == SuspiciousEventType.CLIENT_BLOCKED
    ]

    assert len(blocked) == 1
    assert blocked[0].client_id == registered_client.id
    assert blocked[0].details == {"attempts_total": 3}


def test_login_attempts_are_isolated_per_client(bank, make_client):
    first = make_client()
    second = make_client(
        name="Пётр Петров",
        phone="+79990002233",
        email="petr@example.com",
        pin_code="5678",
    )

    bank.add_client(first)
    bank.add_client(second)

    with pytest.raises(AuthenticationError):
        bank.authenticate_client(first.id, "0000")

    assert bank.authenticate_client(second.id, "5678") is True

    assert bank._login_attempts[first.id] == 1
    assert bank._login_attempts[second.id] == 0


def test_custom_config_max_attempts_respected(bank, registered_client):
    bank._security_config = SecurityConfig(max_login_attempts=5)

    for _ in range(4):
        with pytest.raises(AuthenticationError):
            bank.authenticate_client(registered_client.id, "0000")

    assert registered_client.status == ClientStatus.ACTIVE

    with pytest.raises(ClientBlockedError):
        bank.authenticate_client(registered_client.id, "0000")

    assert registered_client.status == ClientStatus.BLOCKED


# ===========================================================================
# 6. Заморозка и разморозка счетов
# ===========================================================================

def test_freeze_account_sets_status(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    assert bank.freeze_account(account.id) is True
    assert account.status == AccountStatus.FROZEN


def test_freeze_already_frozen_account_returns_false(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    bank.freeze_account(account.id)

    assert bank.freeze_account(account.id) is False


def test_unfreeze_account_restores_active(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    bank.freeze_account(account.id)

    assert bank.unfreeze_account(account.id) is True
    assert account.status == AccountStatus.ACTIVE


def test_unfreeze_active_account_returns_false(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    assert bank.unfreeze_account(account.id) is False


def test_freeze_unknown_account_raises(bank):
    with pytest.raises(AccountNotFoundError):
        bank.freeze_account(uuid4())


def test_unfreeze_unknown_account_raises(bank):
    with pytest.raises(AccountNotFoundError):
        bank.unfreeze_account(uuid4())


# ===========================================================================
# 7. Закрытие счетов
# ===========================================================================

def test_close_account_success(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    assert bank.close_account(account.id) is True
    assert account.status == AccountStatus.CLOSED
    assert account.id in bank.accounts
    assert account.id in registered_client.accounts


def test_close_account_twice_raises(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    bank.close_account(account.id)

    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)


def test_close_account_with_nonzero_balance_raises(bank, registered_client):
    account = open_account_with_balance(bank, registered_client, "100")

    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)


def test_freeze_closed_account_raises(bank, registered_client):
    account = open_rub_account(bank, registered_client)
    bank.close_account(account.id)

    with pytest.raises(InvalidOperationError):
        bank.freeze_account(account.id)


def test_unfreeze_closed_account_raises(bank, registered_client):
    account = open_rub_account(bank, registered_client)
    bank.close_account(account.id)

    with pytest.raises(InvalidOperationError):
        bank.unfreeze_account(account.id)


# ===========================================================================
# 8. Ночной запрет
# ===========================================================================

@pytest.mark.parametrize("hour", [0, 1, 2, 3, 4])
def test_night_operation_forbidden(bank, registered_client, hour):
    with clock_at(hour):
        with pytest.raises(OperationTimeError, match="ночное время"):
            open_rub_account(bank, registered_client)


@pytest.mark.parametrize("hour", [5, 6, 12, 18, 23])
def test_day_operation_allowed(bank, registered_client, hour):
    with clock_at(hour):
        account = open_rub_account(bank, registered_client)

    assert account.id in bank.accounts


def test_night_add_client_forbidden(bank, make_client):
    client = make_client()

    with clock_at(2):
        with pytest.raises(OperationTimeError):
            bank.add_client(client)


def test_night_authentication_forbidden(bank, registered_client):
    with clock_at(2):
        with pytest.raises(OperationTimeError):
            bank.authenticate_client(registered_client.id, "1234")


# ===========================================================================
# 9. Поиск счетов
# ===========================================================================

def test_search_accounts_without_filters(bank, registered_client):
    first = open_rub_account(bank, registered_client)
    second = open_rub_account(bank, registered_client)

    result = bank.search_accounts()

    assert len(result) == 2
    assert first in result
    assert second in result


def test_search_accounts_by_client(bank, registered_client):
    account = open_rub_account(bank, registered_client)

    result = bank.search_accounts(client_id=registered_client.id)

    assert account in result


def test_search_accounts_by_status(bank, registered_client):
    active = open_rub_account(bank, registered_client)
    frozen = open_rub_account(bank, registered_client)

    bank.freeze_account(frozen.id)

    result = bank.search_accounts(status=AccountStatus.FROZEN)

    assert frozen in result
    assert active not in result


def test_search_accounts_invalid_client_filter(bank):
    with pytest.raises(InvalidOperationError):
        bank.search_accounts(client_id="not-uuid")


# ===========================================================================
# 10. Общий баланс
# ===========================================================================

def test_get_total_balance_empty_bank(bank):
    assert bank.get_total_balance() == {}


def test_get_total_balance_single_account(bank, registered_client):
    open_account_with_balance(bank, registered_client, "1000")

    totals = bank.get_total_balance()

    assert totals[Currency.RUB] == Decimal("1000")


def test_get_total_balance_sums_accounts(bank, registered_client):
    open_account_with_balance(bank, registered_client, "1000")
    open_account_with_balance(bank, registered_client, "500")

    totals = bank.get_total_balance()

    assert totals[Currency.RUB] == Decimal("1500")


def test_get_total_balance_excludes_closed_accounts(bank, registered_client):
    account = open_account_with_balance(bank, registered_client, "1000")

    account.withdraw(Decimal("1000"))
    bank.close_account(account.id)

    assert bank.get_total_balance() == {}


def test_get_total_balance_includes_frozen_accounts(bank, registered_client):
    account = open_account_with_balance(bank, registered_client, "1000")
    bank.freeze_account(account.id)

    totals = bank.get_total_balance()

    assert totals[Currency.RUB] == Decimal("1000")


# ===========================================================================
# 11. Рейтинг клиентов
# ===========================================================================

def test_get_clients_ranking_empty_bank(bank):
    assert bank.get_clients_ranking() == {}


def test_get_clients_ranking_sorted_by_balance(bank, make_client):
    first = make_client()
    second = make_client(
        name="Пётр",
        phone="+79990002233",
        email="petr@example.com",
    )
    third = make_client(
        name="Мария",
        phone="+79990003344",
        email="maria@example.com",
    )

    bank.add_client(first)
    bank.add_client(second)
    bank.add_client(third)

    open_account_with_balance(bank, first, "100")
    open_account_with_balance(bank, second, "400")
    open_account_with_balance(bank, second, "400")
    open_account_with_balance(bank, third, "2000")

    ranking = bank.get_clients_ranking()

    rub_ranking = ranking[Currency.RUB]

    assert [total for client, total in rub_ranking] == [
        Decimal("2000"),
        Decimal("800"),
        Decimal("100"),
    ]


def test_get_clients_ranking_excludes_closed_accounts(bank, registered_client):
    account = open_account_with_balance(bank, registered_client, "1000")

    account.withdraw(Decimal("1000"))
    bank.close_account(account.id)

    assert bank.get_clients_ranking() == {}


def test_get_clients_ranking_sums_multiple_accounts(bank, registered_client):
    open_account_with_balance(bank, registered_client, "100")
    open_account_with_balance(bank, registered_client, "200")

    ranking = bank.get_clients_ranking()

    assert ranking[Currency.RUB][0][0] is registered_client
    assert ranking[Currency.RUB][0][1] == Decimal("300")
