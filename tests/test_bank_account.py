"""Тесты для BankAccount.

Покрытие:
- создание счёта (баланс, статус, валюта, id);
- создание с разными валютами (все 5 из требований);
- уникальность полного UUID;
- пополнение и снятие (успех, границы);
- валидация сумм (тип, знак, NaN/Infinity);
- статусы FROZEN / CLOSED (запрет операций, сохранение баланса);
- get_account_info() — все поля;
- __str__ — обязательные фрагменты;
- AbstractAccount нельзя инстанцировать напрямую.
"""

from decimal import Decimal
from datetime import date
from uuid import uuid4

import pytest

from bank_account.abstract_account import AbstractAccount
from client.client import Client
from bank_account.bank_account import BankAccount
from enums.enums import Currency, AccountStatus
from exceptions.exceptions import (
    AccountClosedError,
    AccountFrozenError,
    InsufficientFundsError,
    InvalidOperationError,
)


# ---------- фикстуры ----------

@pytest.fixture
def account(client):
    """RUB-счёт с нулевым балансом и статусом ACTIVE."""
    return BankAccount(owner=client, currency=Currency.RUB)


@pytest.fixture
def frozen_account(account):
    """Счёт в статусе FROZEN.

    Публичного freeze() пока нет, поэтому ставим _status напрямую.
    Когда появится — заменить тело на account.freeze().
    """
    account._status = AccountStatus.FROZEN
    return account


@pytest.fixture
def closed_account(account):
    """Счёт в статусе CLOSED (по той же причине — через _status)."""
    account._status = AccountStatus.CLOSED
    return account


# ---------- 1. Создание счёта ----------

def test_new_account_balance_is_zero(account):
    """Свежий счёт имеет баланс Decimal('0')."""
    assert account.balance == Decimal("0")


def test_new_account_balance_is_decimal_not_float(account):
    """Баланс именно Decimal — float копит ошибки округления."""
    assert isinstance(account.balance, Decimal)


def test_new_account_status_is_active(account):
    """Новый счёт сразу ACTIVE."""
    assert account.status == AccountStatus.ACTIVE


def test_new_account_currency_is_rub(account):
    """Валюта сохраняется такой, какой передана."""
    assert account.currency == Currency.RUB


def test_account_id_is_uuid(client):
    """account.id — UUID.

    Важно: короткий id предназначен ТОЛЬКО для отображения.
    Уникальность счёта гарантируется полным UUID (_id), а не этими
    4 символами — совпадение теоретически возможно (см. тест
    test_two_accounts_have_different_full_uuids).
    """
    full_id = uuid4()
    acc = BankAccount(owner=client, currency=Currency.RUB, account_id=full_id)
    assert acc.id == full_id


def test_auto_generated_id_is_uuid(account):
    """Если UUID не передан, id  генерируется."""
    from uuid import UUID
    assert isinstance(account.id, UUID)


def test_two_accounts_have_different_full_uuids(client):
    """ Два независимых счёта имеют разные полные UUID. """
    first = BankAccount(owner=client, currency=Currency.RUB)
    second = BankAccount(owner=client, currency=Currency.RUB)
    assert first._id != second._id


# ---------- 2. Валюты ----------

@pytest.mark.parametrize(
    "currency",
    [Currency.RUB, Currency.USD, Currency.EUR, Currency.KZT, Currency.CNY],
    ids=["rub", "usd", "eur", "kzt", "cny"],
)
def test_create_account_with_various_currencies(client, currency):
    """Счёт можно создать с любой валютой из требований."""
    account = BankAccount(owner=client, currency=currency)
    assert account.currency == currency


# ---------- 3. Пополнения ----------

def test_deposit_1000_sets_balance(account):
    """Пополнение на 1000 → баланс 1000."""
    account.deposit(Decimal("1000"))
    assert account.balance == Decimal("1000")


def test_deposit_500_after_1000_accumulates(account):
    """1000 + 500 = 1500 — депозит аддитивен."""
    account.deposit(Decimal("1000"))
    account.deposit(Decimal("500"))
    assert account.balance == Decimal("1500")


def test_deposit_is_additive_not_replacing(account):
    """250 + 250 = 500 — не перезапись, а накопление."""
    account.deposit(Decimal("250"))
    account.deposit(Decimal("250"))
    assert account.balance == Decimal("500")


# ---------- 4. Ошибочные суммы при пополнении ----------

def test_deposit_zero_raises(account):
    """Нулевое пополнение недопустимо."""
    with pytest.raises(InvalidOperationError):
        account.deposit(Decimal("0"))


def test_deposit_negative_raises(account):
    """Отрицательное пополнение недопустимо."""
    with pytest.raises(InvalidOperationError):
        account.deposit(Decimal("-100"))


def test_deposit_float_raises(account):
    """float отклоняется — деньги только в Decimal."""
    with pytest.raises(InvalidOperationError):
        account.deposit(1000.0)


def test_deposit_string_raises(account):
    """Строка отклоняется — ожидается Decimal."""
    with pytest.raises(InvalidOperationError):
        account.deposit("1000")


def test_deposit_int_raises(account):
    """int отклоняется — принимаем только Decimal."""
    with pytest.raises(InvalidOperationError):
        account.deposit(1000)


def test_deposit_nan_raises(account):
    """NaN — не число, отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.deposit(Decimal("NaN"))


def test_deposit_infinity_raises(account):
    """Бесконечность отклоняется — баланс не должен стать Infinity."""
    with pytest.raises(InvalidOperationError):
        account.deposit(Decimal("Infinity"))


# ---------- 5. Снятие денег ----------

def test_withdraw_part_of_balance(account):
    """1000 − 300 = 700."""
    account.deposit(Decimal("1000"))
    account.withdraw(Decimal("300"))
    assert account.balance == Decimal("700")


def test_withdraw_entire_balance(account):
    """Снять всё можно — баланс становится 0 (не ошибка)."""
    account.deposit(Decimal("1000"))
    account.withdraw(Decimal("1000"))
    assert account.balance == Decimal("0")


def test_withdraw_insufficient_funds_raises(account):
    """Снять больше баланса нельзя — InsufficientFundsError."""
    account.deposit(Decimal("1000"))
    with pytest.raises(InsufficientFundsError):
        account.withdraw(Decimal("1500"))


def test_withdraw_insufficient_funds_preserves_balance(account):
    """После InsufficientFundsError баланс не тронут."""
    account.deposit(Decimal("1000"))
    with pytest.raises(InsufficientFundsError):
        account.withdraw(Decimal("1500"))
    assert account.balance == Decimal("1000")


# ---------- 6. Ошибочные суммы при снятии ----------

def test_withdraw_zero_raises(account):
    """Нулевое снятие отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("0"))


def test_withdraw_negative_raises(account):
    """Отрицательное снятие отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("-100"))


def test_withdraw_float_raises(account):
    """float отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(500.0)


def test_withdraw_string_raises(account):
    """Строка отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw("500")


def test_withdraw_int_raises(account):
    """int отклоняется — только Decimal."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(500)


def test_withdraw_nan_raises(account):
    """NaN отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("NaN"))


def test_withdraw_infinity_raises(account):
    """Infinity отклоняется."""
    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("Infinity"))


# ---------- 7. Баланс не меняется при ошибках снятия ----------

BAD_AMOUNTS = [
    Decimal("0"),
    Decimal("-100"),
    500.0,
    "500",
    500,
    Decimal("NaN"),
    Decimal("Infinity"),
]

BAD_AMOUNTS_IDS = ["zero", "negative", "float", "str", "int", "nan", "inf"]


@pytest.mark.parametrize("bad_amount", BAD_AMOUNTS, ids=BAD_AMOUNTS_IDS)
def test_failed_withdraw_does_not_change_balance(account, bad_amount):
    """Любая некорректная сумма не должна испортить баланс."""
    account.deposit(Decimal("1000"))
    with pytest.raises(InvalidOperationError):
        account.withdraw(bad_amount)
    assert account.balance == Decimal("1000")


def test_failed_withdraw_insufficient_funds_does_not_change_balance(account):
    """Попытка снять больше баланса не меняет баланс."""
    account.deposit(Decimal("1000"))
    with pytest.raises(InsufficientFundsError):
        account.withdraw(Decimal("1000.01"))
    assert account.balance == Decimal("1000")


# ---------- 8. Статусы FROZEN / CLOSED ----------
#
# Замечание: отдельные тесты ниже проверяют только тип исключения,
# а параметризованный test_failed_operation_on_blocked_account_...
# повторяет их и дополнительно проверяет сохранение баланса.
# Это сознательное дублирование: при падении сразу видно, что сломалось —
# конкретная операция (deposit/withdraw) или инвариант баланса.

def test_frozen_account_deposit_raises(frozen_account):
    """Замороженный счёт не принимает пополнения."""
    with pytest.raises(AccountFrozenError):
        frozen_account.deposit(Decimal("100"))


def test_frozen_account_withdraw_raises(frozen_account):
    """Замороженный счёт не даёт снимать."""
    frozen_account._balance = Decimal("1000")
    with pytest.raises(AccountFrozenError):
        frozen_account.withdraw(Decimal("100"))


def test_closed_account_deposit_raises(closed_account):
    """Закрытый счёт не принимает пополнения."""
    with pytest.raises(AccountClosedError):
        closed_account.deposit(Decimal("100"))


def test_closed_account_withdraw_raises(closed_account):
    """Закрытый счёт не даёт снимать."""
    closed_account._balance = Decimal("1000")
    with pytest.raises(AccountClosedError):
        closed_account.withdraw(Decimal("100"))


@pytest.mark.parametrize("status,exc,amount", [
    (AccountStatus.FROZEN, AccountFrozenError, Decimal("100")),
    (AccountStatus.CLOSED, AccountClosedError, Decimal("100")),
], ids=["frozen", "closed"])
def test_failed_operation_on_blocked_account_does_not_change_balance(
    account, status, exc, amount
):
    """Операции на заблокированном счёте не меняют баланс."""
    account.deposit(Decimal("500"))
    account._status = status
    with pytest.raises(exc):
        account.deposit(amount)
    with pytest.raises(exc):
        account.withdraw(amount)
    assert account.balance == Decimal("500")


# ---------- 9. get_account_info ----------

def test_get_account_info_returns_dict(account):
    """get_account_info возвращает словарь."""
    assert isinstance(account.get_account_info(), dict)


def test_get_account_info_contains_required_fields(account):
    """В словаре есть все обязательные ключи."""
    info = account.get_account_info()
    required = {"id", "type", "owner", "status", "balance", "currency"}
    assert required.issubset(info.keys())


def test_get_account_info_returns_correct_values(account):
    """Значения в словаре соответствуют атрибутам счёта, включая type."""
    account.deposit(Decimal("1000"))
    info = account.get_account_info()
    assert info["id"] == str(account.id)[-4:]
    assert info["type"] == "BankAccount"
    assert info["owner"] == "Иван Иванов"
    assert info["balance"] == Decimal("1000")
    assert info["currency"] == "RUB"
    assert info["status"] == "Активный"


# ---------- 10. __str__ ----------

def test_str_contains_account_type(account):
    """В строке присутствует полное название счёта."""
    assert "Банковский счет" in str(account)


def test_str_contains_owner_name(account):
    """В строке присутствует имя владельца."""
    assert "Иван Иванов" in str(account)


def test_str_contains_account_id(account):
    """В строке есть последние 4 символа UUID (account.id)."""
    assert str(account.id)[-4:] in str(account)


def test_str_contains_status(account):
    """В строке отображается русское название статуса."""
    assert "Активный" in str(account)


def test_str_contains_balance(account):
    """В строке есть значение баланса."""
    account.deposit(Decimal("1000"))
    assert "1000" in str(account)


def test_str_contains_currency(account):
    """В строке присутствует ISO-код валюты."""
    assert "RUB" in str(account)


# ---------- 11. Баланс не меняется при ошибке пополнения ----------

@pytest.mark.parametrize("bad_amount", [
    Decimal("0"),
    Decimal("-100"),
    1000.0,
    "1000",
    1000,
    Decimal("NaN"),
    Decimal("Infinity"),
], ids=["zero", "negative", "float", "str", "int", "nan", "inf"])
def test_failed_deposit_does_not_change_balance(account, bad_amount):
    """Некорректное пополнение не портит баланс."""
    account.deposit(Decimal("500"))
    with pytest.raises(InvalidOperationError):
        account.deposit(bad_amount)
    assert account.balance == Decimal("500")


# ---------- 12. AbstractAccount нельзя создать напрямую ----------

def test_cannot_instantiate_abstract_account(client):
    """AbstractAccount — абстрактный, инстанцировать нельзя.

    Требует, чтобы класс наследовал abc.ABC и имел хотя бы один
    @abstractmethod. Если тест падает с DID NOT RAISE — значит
    этого ещё нет: добавь ABC и пометь методы абстрактными.
    """
    with pytest.raises(TypeError):
        AbstractAccount(owner=client)

# ---------- 13. Тесты проверок после ревью ----------
def test_bank_account_rejects_invalid_owner():
    with pytest.raises(InvalidOperationError):
        BankAccount(
            owner="Иван",
            currency=Currency.RUB
        )


def test_bank_account_rejects_invalid_currency(client):
    with pytest.raises(InvalidOperationError):
        BankAccount(
            owner=client,
            currency="RUB"
        )


def test_bank_account_rejects_invalid_account_id(client):
    with pytest.raises(InvalidOperationError):
        BankAccount(
            owner=client,
            currency=Currency.RUB,
            account_id="12345"
        )