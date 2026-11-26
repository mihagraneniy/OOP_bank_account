import copy
import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from bank.bank import Bank
from bank_account.bank_account import BankAccount
from bank_account.savings_account import SavingsAccount
from bank_account.investment_account import InvestmentAccount
from bank_account.premium_account import PremiumAccount
from client.client import Client
from enums.enums import ClientStatus, Currency, AccountType, AccountStatus
from exceptions.exceptions import InvalidOperationError, AccountNotFoundError


# ---------------------------------------------------------------------------
# Базовые тесты банка
# ---------------------------------------------------------------------------

def test_bank_creation():
    bank = Bank("Тестовый банк")
    assert bank.name == "Тестовый банк"
    assert bank.clients == {}
    assert bank.accounts == {}


def test_bank_rejects_empty_name():
    with pytest.raises(InvalidOperationError):
        Bank("")


def test_add_client(bank, client):
    bank.add_client(client)
    assert client.id in bank.clients
    assert bank.clients[client.id] is client


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


def test_accounts_property_returns_copy(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    snapshot = bank.accounts
    snapshot["sentinel"] = object()
    assert bank.accounts[account.id] is account
    assert "sentinel" not in bank.accounts


def test_clients_property_returns_copy(bank, registered_client):
    snapshot = bank.clients
    snapshot["sentinel"] = object()
    assert bank.clients[registered_client.id] is registered_client
    assert "sentinel" not in bank.clients


# ---------------------------------------------------------------------------
# open_account
# ---------------------------------------------------------------------------

def test_open_account_debet(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    assert type(account) is BankAccount
    assert bank.accounts[account.id] is account
    assert account.id in registered_client.accounts
    assert account.owner is registered_client
    assert account.status == AccountStatus.ACTIVE


def test_open_account_saving(bank, registered_client):
    account = bank.open_account(
        registered_client, AccountType.SAVING, Currency.RUB,
        min_balance=Decimal("100"), monthly_interest_rate=Decimal("0.05"),
    )
    assert isinstance(account, SavingsAccount)
    assert bank.accounts[account.id] is account
    assert account.id in registered_client.accounts


def test_open_account_investment(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.INVESTMENT, Currency.RUB)
    assert isinstance(account, InvestmentAccount)
    assert bank.accounts[account.id] is account


def test_open_account_premium(bank, registered_client):
    account = bank.open_account(
        registered_client, AccountType.PREMIUM, Currency.RUB,
        max_withdrawal=Decimal("50000"),
        overdraft_limit=Decimal("10000"),
        fixed_fee=Decimal("100"),
    )
    assert isinstance(account, PremiumAccount)
    assert bank.accounts[account.id] is account


def test_open_account_uses_registered_client_instance(bank, client):
    """
    Счёт привязывается к зарегистрированному экземпляру клиента,
    а не к переданному «клону» с тем же UUID.

    deepcopy нужен, чтобы `other.accounts` был независимым списком;
    при copy.copy он делит список с оригиналом.
    """
    bank.add_client(client)

    other = copy.deepcopy(client)
    assert other.id == client.id
    assert other is not client
    assert other.accounts is not client.accounts

    account = bank.open_account(other, AccountType.DEBET, Currency.RUB)

    assert account.owner is client
    assert account.owner is not other
    assert account.id in client.accounts
    assert account.id not in other.accounts


def test_open_account_unregistered_client_raises(bank, client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(client, AccountType.DEBET, Currency.RUB)


def test_open_account_inactive_client_raises(bank, registered_client):
    registered_client.status = ClientStatus.BLOCKED
    with pytest.raises(InvalidOperationError):
        bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)


def test_open_account_non_client_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.open_account("not a client", AccountType.DEBET, Currency.RUB)


def test_open_account_invalid_account_type_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(registered_client, "DEBET", Currency.RUB)


def test_open_account_invalid_currency_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(registered_client, AccountType.DEBET, "RUB")


def test_open_account_saving_missing_params_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(registered_client, AccountType.SAVING, Currency.RUB)


def test_open_account_premium_missing_params_raises(bank, registered_client):
    with pytest.raises(InvalidOperationError):
        bank.open_account(registered_client, AccountType.PREMIUM, Currency.RUB)


def test_open_account_repeated_calls_create_distinct_accounts(bank, registered_client):
    a1 = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    a2 = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    assert a1.id != a2.id
    assert a1.id in bank.accounts and a2.id in bank.accounts
    assert a1.id in registered_client.accounts
    assert a2.id in registered_client.accounts


# ---------------------------------------------------------------------------
# close_account
# ---------------------------------------------------------------------------

def test_close_account_success(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.close_account(account.id)
    assert account.id in bank.accounts
    assert account.id in registered_client.accounts
    assert account.status == AccountStatus.CLOSED


def test_close_account_invalid_uuid_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.close_account("not-a-uuid")


def test_close_account_not_found_raises(bank):
    with pytest.raises(AccountNotFoundError):
        bank.close_account(uuid4())


def test_close_account_twice_raises(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.close_account(account.id)
    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)


def _set_balance_for_test(account, value: Decimal) -> None:
    """
    Тестовый хелпер: у BankAccount нет публичного сеттера balance,
    поэтому пишем напрямую в приватное поле.

    ВНИМАНИЕ: это завязка на внутреннее устройство класса.
    Когда появится публичный API (deposit/withdraw/сеттер), заменить здесь
    и только здесь — тесты останутся нетронутыми.
    """
    account._balance = value


def test_close_account_positive_balance_raises(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    _set_balance_for_test(account, Decimal("100"))

    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)

    assert account.id in bank.accounts


def test_close_account_negative_balance_raises(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    _set_balance_for_test(account, Decimal("-50"))  # отрицательный — тоже ненулевой

    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)

    assert account.id in bank.accounts


def test_close_account_already_closed_status_branch(bank, registered_client):
    """
    Дефензивная ветка: счёт со статусом CLOSED, но всё ещё в реестре
    (в нормальном флоу недостижима — close_account удаляет из реестра).
    """
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    account.change_account_status(AccountStatus.CLOSED)

    with pytest.raises(InvalidOperationError):
        bank.close_account(account.id)


# ---------------------------------------------------------------------------
# freeze_account / unfreeze_account
# ---------------------------------------------------------------------------

def test_freeze_account_success(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    changed = bank.freeze_account(account.id)
    assert changed is True
    assert account.status == AccountStatus.FROZEN
    assert account.id in bank.accounts


def test_freeze_account_already_frozen_returns_false(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.freeze_account(account.id)
    changed = bank.freeze_account(account.id)
    assert changed is False
    assert account.status == AccountStatus.FROZEN


def test_freeze_account_not_found_raises(bank):
    with pytest.raises(AccountNotFoundError):
        bank.freeze_account(uuid4())


def test_freeze_account_invalid_uuid_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.freeze_account("not-a-uuid")


def test_freeze_account_after_close_raises_invalid_operation(bank, registered_client):
    """
    После close_account счёт не удаляется из реестра, поэтому freeze_account
    видит именно InvalidOperationError.
    Это соответствует текущей реализации (закрытие != удаление из _accounts).
    """
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.close_account(account.id)
    with pytest.raises(InvalidOperationError):
        bank.freeze_account(account.id)


def test_unfreeze_account_success(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.freeze_account(account.id)
    changed = bank.unfreeze_account(account.id)
    assert changed is True
    assert account.status == AccountStatus.ACTIVE


def test_unfreeze_account_already_active_returns_false(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    changed = bank.unfreeze_account(account.id)
    assert changed is False
    assert account.status == AccountStatus.ACTIVE


def test_unfreeze_account_not_found_raises(bank):
    with pytest.raises(AccountNotFoundError):
        bank.unfreeze_account(uuid4())


def test_unfreeze_account_invalid_uuid_raises(bank):
    with pytest.raises(InvalidOperationError):
        bank.unfreeze_account("not-a-uuid")


def test_unfreeze_account_after_close_raises_invalid_operation(bank, registered_client):
    """Симметрично freeze_account_after_close: счёт удалён -> AccountNotFoundError."""
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.close_account(account.id)
    with pytest.raises(InvalidOperationError):
        bank.unfreeze_account(account.id)


# ---------------------------------------------------------------------------
# Сквозные сценарии
# ---------------------------------------------------------------------------

def test_account_full_lifecycle(bank, registered_client):
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    assert account.status == AccountStatus.ACTIVE

    assert bank.freeze_account(account.id) is True
    assert account.status == AccountStatus.FROZEN
    assert bank.freeze_account(account.id) is False

    assert bank.unfreeze_account(account.id) is True
    assert account.status == AccountStatus.ACTIVE
    assert bank.unfreeze_account(account.id) is False

    bank.close_account(account.id)
    assert account.id in bank.accounts
    assert account.id in registered_client.accounts
    assert account.status == AccountStatus.CLOSED


def test_frozen_account_can_be_closed_if_zero_balance(bank, registered_client):
    """Заморозка не блокирует закрытие с нулевым балансом — это разные оси."""
    account = bank.open_account(registered_client, AccountType.DEBET, Currency.RUB)
    bank.freeze_account(account.id)
    bank.close_account(account.id)
    assert account.id in bank.accounts
    assert account.status == AccountStatus.CLOSED


def test_multiple_clients_isolated(bank, client):
    bank.add_client(client)
    other = Client(
        name="Пётр Петров",
        birth_date=date(1985, 5, 5),
        phone="+79990002233",
        email="petr@example.com",
        pin_code="1234"
    )
    bank.add_client(other)

    a1 = bank.open_account(client, AccountType.DEBET, Currency.RUB)
    a2 = bank.open_account(other, AccountType.DEBET, Currency.USD)

    assert a1.id in client.accounts and a1.id not in other.accounts
    assert a2.id in other.accounts and a2.id not in client.accounts