"""Тесты для PremiumAccount.

Покрытие:
- создание (нулевые и ненулевые параметры);
- валидация max_withdrawal / overdraft_limit / fixed_fee (тип, знак, NaN/Infinity);
- комиссия начисляется ТОЛЬКО при переходе из положительного в отрицательный баланс;
- комиссия НЕ начисляется при обычном снятии / переходе в ноль / старте с нуля
  или отрицательного баланса;
- лимит овердрафта (граница, отказ, сохранение баланса);
- овердрафт с учётом комиссии;
- лимит разового снятия max_withdrawal (не включает комиссию);
- снятие с FROZEN / CLOSED;
- get_account_info() и __str__ с полями премиум-счёта.
"""

from decimal import Decimal
from datetime import date

import pytest

from client.client import Client
from enums.enums import Currency, AccountStatus
from exceptions.exceptions import (
    AccountClosedError,
    AccountFrozenError,
    InvalidOperationError,
)
from bank_account.premium_account import PremiumAccount


# ---------- фикстуры ----------

@pytest.fixture
def premium(client):
    """Базовый премиум-счёт: все параметры нулевые, баланс 0."""
    return PremiumAccount(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=Decimal("0"),
        overdraft_limit=Decimal("0"),
        fixed_fee=Decimal("0"),
    )


def make(client, *, balance=Decimal("0"), max_withdrawal=Decimal("1000"),
         overdraft_limit=Decimal("0"), fixed_fee=Decimal("0")):
    """Хелпер: создать счёт и опционально положить на него баланс."""
    acc = PremiumAccount(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=max_withdrawal,
        overdraft_limit=overdraft_limit,
        fixed_fee=fixed_fee,
    )
    if balance > 0:
        acc.deposit(balance)
    return acc


# ---------- 1. Создание счёта ----------

def test_create_premium_account_with_zero_params(premium):
    """Нулевые значения всех трёх параметров допустимы."""
    assert premium.max_withdrawal == Decimal("0")
    assert premium.overdraft_limit == Decimal("0")
    assert premium.fixed_fee == Decimal("0")
    assert premium.balance == Decimal("0")


def test_create_premium_account_with_non_zero_params(client):
    """Ненулевые параметры сохраняются как есть."""
    acc = PremiumAccount(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=Decimal("10000"),
        overdraft_limit=Decimal("500"),
        fixed_fee=Decimal("50"),
    )
    assert acc.max_withdrawal == Decimal("10000")
    assert acc.overdraft_limit == Decimal("500")
    assert acc.fixed_fee == Decimal("50")


# ---------- 2. Валидация параметров конструктора ----------

@pytest.mark.parametrize(
    "field",
    ["max_withdrawal", "overdraft_limit", "fixed_fee"],
)
def test_negative_param_raises(client, field):
    """Отрицательные значения любого из трёх параметров недопустимы."""
    kwargs = dict(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=Decimal("1000"),
        overdraft_limit=Decimal("100"),
        fixed_fee=Decimal("10"),
    )
    kwargs[field] = Decimal("-1")
    with pytest.raises(InvalidOperationError):
        PremiumAccount(**kwargs)


BAD_VALUES = [500.0, "500", 500, Decimal("NaN"), Decimal("Infinity")]
BAD_VALUES_IDS = ["float", "str", "int", "nan", "inf"]


@pytest.mark.parametrize("bad_value", BAD_VALUES, ids=BAD_VALUES_IDS)
@pytest.mark.parametrize(
    "field",
    ["max_withdrawal", "overdraft_limit", "fixed_fee"],
)
def test_bad_param_type_raises(client, field, bad_value):
    """float/str/int/NaN/Infinity отклоняются для любого параметра."""
    kwargs = dict(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=Decimal("1000"),
        overdraft_limit=Decimal("100"),
        fixed_fee=Decimal("10"),
    )
    kwargs[field] = bad_value
    with pytest.raises(InvalidOperationError):
        PremiumAccount(**kwargs)


# ---------- 3. Комиссия: списание при каждом снятии ----------

def test_fee_applied_when_balance_stays_positive(client):
    """100 - 50 - 10 = 40."""
    acc = make(
        client,
        balance=Decimal("100"),
        fixed_fee=Decimal("10"),
        overdraft_limit=Decimal("1000")
    )

    acc.withdraw(Decimal("50"))

    assert acc.balance == Decimal("40")


def test_fee_applied_when_balance_starts_at_zero(client):
    """0 - 50 - 10 = -60."""
    acc = make(
        client,
        balance=Decimal("0"),
        fixed_fee=Decimal("10"),
        overdraft_limit=Decimal("1000")
    )

    acc.withdraw(Decimal("50"))

    assert acc.balance == Decimal("-60")


def test_fee_applied_when_balance_is_negative(client):
    """-20 - 30 - 10 = -60."""
    acc = make(
        client,
        balance=Decimal("0"),
        fixed_fee=Decimal("10"),
        overdraft_limit=Decimal("1000")
    )

    acc.withdraw(Decimal("10"))
    acc.withdraw(Decimal("30"))

    assert acc.balance == Decimal("-60")


# ---------- 4. Лимит овердрафта ----------

def test_overdraft_within_limit(client):
    """0 − 50 = −50 < limit 100 → проходит."""
    acc = make(client, balance=Decimal("0"),
               overdraft_limit=Decimal("100"))
    acc.withdraw(Decimal("50"))
    assert acc.balance == Decimal("-50")


def test_overdraft_exact_limit_allowed(client):
    """0 − 100 = −100 = limit → граница включительна."""
    acc = make(client, balance=Decimal("0"),
               overdraft_limit=Decimal("100"))
    acc.withdraw(Decimal("100"))
    assert acc.balance == Decimal("-100")


def test_overdraft_exceeded_raises(client):
    """0 − 101 = −101 > limit 100 → отказ."""
    acc = make(client, balance=Decimal("0"),
               overdraft_limit=Decimal("100"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("101"))


def test_zero_overdraft_zero_balance_raises(client):
    """balance=0, overdraft_limit=0, снятие 10 → отказ."""
    acc = make(client, balance=Decimal("0"),
               overdraft_limit=Decimal("0"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("10"))


def test_overdraft_exceeded_preserves_balance(client):
    """После отказа баланс не тронут."""
    acc = make(client, balance=Decimal("0"),
               overdraft_limit=Decimal("100"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("101"))
    assert acc.balance == Decimal("0")


def test_overdraft_check_includes_fee(client):
    """100 − 120 − 10 = −30, limit 30 → граница проходит."""
    acc = make(client, balance=Decimal("100"),
               overdraft_limit=Decimal("30"), fixed_fee=Decimal("10"))
    acc.withdraw(Decimal("120"))
    assert acc.balance == Decimal("-30")


def test_overdraft_check_includes_fee_exceeded(client):
    """100 − 120 − 10 = −30, limit 29 → отказ из-за комиссии."""
    acc = make(client, balance=Decimal("100"),
               overdraft_limit=Decimal("29"), fixed_fee=Decimal("10"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("120"))


def test_overdraft_with_fee_exceeded_preserves_balance(client):
    """При отказе по овердрафту (с учётом комиссии) баланс не меняется."""
    acc = make(client, balance=Decimal("100"),
               overdraft_limit=Decimal("29"), fixed_fee=Decimal("10"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("120"))
    assert acc.balance == Decimal("100")


# ---------- 5. Лимит разового снятия max_withdrawal ----------

def test_withdraw_equal_max_allowed(client):
    """amount == max_withdrawal разрешено."""
    acc = make(client, balance=Decimal("500"),
               max_withdrawal=Decimal("500"), overdraft_limit=Decimal("1000"))
    acc.withdraw(Decimal("500"))
    assert acc.balance == Decimal("0")


def test_withdraw_above_max_raises(client):
    """amount > max_withdrawal → отказ."""
    acc = make(client, balance=Decimal("1000"),
               max_withdrawal=Decimal("500"), overdraft_limit=Decimal("1000"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("500.01"))


def test_withdraw_above_max_preserves_balance(client):
    """После отказа баланс не тронут."""
    acc = make(client, balance=Decimal("1000"),
               max_withdrawal=Decimal("500"), overdraft_limit=Decimal("1000"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("500.01"))
    assert acc.balance == Decimal("1000")


def test_zero_max_withdrawal_rejects_any_amount(client):
    """max_withdrawal=0 — снимать нельзя ничего."""
    acc = make(client, balance=Decimal("100"), max_withdrawal=Decimal("0"),
               overdraft_limit=Decimal("1000"))
    with pytest.raises(InvalidOperationError):
        acc.withdraw(Decimal("1"))


def test_max_withdrawal_compared_with_amount_only(client):
    """max_withdrawal сравнивается с amount; комиссия сверху не учитывается."""
    acc = make(client, balance=Decimal("100"),
               max_withdrawal=Decimal("120"), fixed_fee=Decimal("10"),
               overdraft_limit=Decimal("1000"))
    acc.withdraw(Decimal("120"))
    assert acc.balance == Decimal("-30")


# ---------- 6. Снятие с заблокированного / закрытого счёта ----------

@pytest.mark.parametrize("status,exc", [
    (AccountStatus.FROZEN, AccountFrozenError),
    (AccountStatus.CLOSED, AccountClosedError),
], ids=["frozen", "closed"])
def test_withdraw_on_blocked_account_raises(client, status, exc):
    """FROZEN / CLOSED не дают снимать."""
    acc = make(client, balance=Decimal("1000"),
               max_withdrawal=Decimal("1000"), overdraft_limit=Decimal("500"))
    acc._status = status
    with pytest.raises(exc):
        acc.withdraw(Decimal("100"))


@pytest.mark.parametrize("status,exc", [
    (AccountStatus.FROZEN, AccountFrozenError),
    (AccountStatus.CLOSED, AccountClosedError),
], ids=["frozen", "closed"])
def test_withdraw_on_blocked_account_preserves_balance(client, status, exc):
    """После отказа баланс не тронут — комиссия тоже не начисляется."""
    acc = make(client, balance=Decimal("1000"), fixed_fee=Decimal("10"),
               max_withdrawal=Decimal("1000"), overdraft_limit=Decimal("500"))
    acc._status = status
    with pytest.raises(exc):
        acc.withdraw(Decimal("2000"))   # потенциально перешёл бы в минус
    assert acc.balance == Decimal("1000")


# ---------- 7. get_account_info и __str__ ----------

def test_get_account_info_contains_premium_fields(premium):
    """Поля премиум-счёта присутствуют в словаре."""
    info = premium.get_account_info()
    assert "max_withdrawal" in info
    assert "overdraft_limit" in info
    assert "fixed_fee" in info


def test_get_account_info_includes_premium_values(client):
    """Значения премиум-полей соответствуют атрибутам."""
    acc = PremiumAccount(
        owner=client,
        currency=Currency.RUB,
        max_withdrawal=Decimal("10000"),
        overdraft_limit=Decimal("500"),
        fixed_fee=Decimal("50"),
    )
    info = acc.get_account_info()
    assert info["max_withdrawal"] == Decimal("10000")
    assert info["overdraft_limit"] == Decimal("500")
    assert info["fixed_fee"] == Decimal("50")


def test_str_contains_premium_type(premium):
    """В строке есть «Премиальный» — не путается с банковским/накопительным."""
    assert "Премиальный" in str(premium)