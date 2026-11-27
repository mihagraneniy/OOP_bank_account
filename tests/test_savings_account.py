"""Тесты для SavingsAccount.

Покрытие:
- создание (нулевые и ненулевые параметры);
- валидация min_balance / monthly_interest_rate (тип, знак, NaN/Infinity);
- начисление процентов с ROUND_HALF_UP;
- начисление процентов на FROZEN / CLOSED;
- снятие с сохранением min_balance (успех, граница, отказ);
- get_account_info() и __str__ с полями накопительного счёта.
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
from bank_account.savings_account import SavingsAccount


# ---------- фикстуры ----------

@pytest.fixture
def savings(client):
    """Базовый счёт: min_balance=0, rate=0, баланс 0."""
    return SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("0"),
        monthly_interest_rate=Decimal("0"),
    )

# ---------- 1. Создание счёта ----------

def test_create_savings_account_with_zero_min_balance_and_zero_rate(savings):
    """min_balance=0 и rate=0 — допустимы (strict=False в валидаторе)."""
    assert savings.min_balance == Decimal("0")
    assert savings.monthly_interest_rate == Decimal("0")
    assert savings.balance == Decimal("0")


def test_create_savings_account_with_non_zero_params(client):
    """Ненулевые параметры сохраняются как есть."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.05"),
    )
    assert account.min_balance == Decimal("500")
    assert account.monthly_interest_rate == Decimal("0.05")


# ---------- 2. Валидация параметров конструктора ----------

def test_negative_min_balance_raises(client):
    """Отрицательный min_balance недопустим."""
    with pytest.raises(InvalidOperationError):
        SavingsAccount(
            owner=client,
            currency=Currency.RUB,
            min_balance=Decimal("-1"),
            monthly_interest_rate=Decimal("0"),
        )


def test_negative_monthly_interest_rate_raises(client):
    """Отрицательная ставка недопустима."""
    with pytest.raises(InvalidOperationError):
        SavingsAccount(
            owner=client,
            currency=Currency.RUB,
            min_balance=Decimal("0"),
            monthly_interest_rate=Decimal("-0.01"),
        )


BAD_VALUES = [500.0, "500", 500, Decimal("NaN"), Decimal("Infinity")]
BAD_VALUES_IDS = ["float", "str", "int", "nan", "inf"]


@pytest.mark.parametrize("bad_value", BAD_VALUES, ids=BAD_VALUES_IDS)
def test_bad_min_balance_raises(client, bad_value):
    """min_balance: float/str/int/NaN/Infinity отклоняются."""
    with pytest.raises(InvalidOperationError):
        SavingsAccount(
            owner=client,
            currency=Currency.RUB,
            min_balance=bad_value,
            monthly_interest_rate=Decimal("0"),
        )


@pytest.mark.parametrize("bad_value", BAD_VALUES, ids=BAD_VALUES_IDS)
def test_bad_monthly_interest_rate_raises(client, bad_value):
    """monthly_interest_rate: float/str/int/NaN/Infinity отклоняются."""
    with pytest.raises(InvalidOperationError):
        SavingsAccount(
            owner=client,
            currency=Currency.RUB,
            min_balance=Decimal("0"),
            monthly_interest_rate=bad_value,
        )


# ---------- 3. Начисление процентов ----------

def test_apply_monthly_interest_rounds_half_up(client):
    """1 × 0.005 = 0.005 → ROUND_HALF_UP → 0.01.

    Ровно граница .5 копейки: ROUND_HALF_EVEN дал бы 0.00.
    """
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("0"),
        monthly_interest_rate=Decimal("0.005"),
    )
    account.deposit(Decimal("1"))

    result = account.apply_monthly_interest()

    assert result == Decimal("1.01")
    assert account.balance == Decimal("1.01")


def test_apply_monthly_interest_typical_case(client):
    """1000 под 1% → +10.00, баланс 1010.00."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("0"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))

    account.apply_monthly_interest()

    assert account.balance == Decimal("1010.00")


# ---------- 4. Начисление процентов на заблокированном счёте ----------

@pytest.mark.parametrize("status,exc", [
    (AccountStatus.FROZEN, AccountFrozenError),
    (AccountStatus.CLOSED, AccountClosedError),
], ids=["frozen", "closed"])
def test_blocked_account_interest_raises(client, status, exc):
    """FROZEN / CLOSED не дают начислять проценты."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("0"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))
    account._status = status

    with pytest.raises(exc):
        account.apply_monthly_interest()


@pytest.mark.parametrize("status,exc", [
    (AccountStatus.FROZEN, AccountFrozenError),
    (AccountStatus.CLOSED, AccountClosedError),
], ids=["frozen", "closed"])
def test_blocked_account_interest_preserves_balance(client, status, exc):
    """После отказа баланс не меняется — проценты не начислились."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("0"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))
    account._status = status

    with pytest.raises(exc):
        account.apply_monthly_interest()

    assert account.balance == Decimal("1000")


# ---------- 5. Снятие с сохранением min_balance ----------

def test_withdraw_keeps_balance_above_min(client):
    """1000 − 300 = 700 ≥ 500 → операция проходит."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))

    account.withdraw(Decimal("300"))

    assert account.balance == Decimal("700")


def test_withdraw_down_to_min_balance(client):
    """Снятие ровно до min_balance — граница включительна."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))

    account.withdraw(Decimal("500"))

    assert account.balance == Decimal("500")


def test_withdraw_below_min_balance_raises(client):
    """1000 − 600 = 400 < 500 → InvalidOperationError."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))

    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("600"))


def test_withdraw_below_min_balance_preserves_balance(client):
    """После отказа баланс не тронут."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.01"),
    )
    account.deposit(Decimal("1000"))

    with pytest.raises(InvalidOperationError):
        account.withdraw(Decimal("600"))

    assert account.balance == Decimal("1000")


# ---------- 6. get_account_info и __str__ ----------

def test_get_account_info_contains_savings_fields(savings):
    """Накопительные поля присутствуют в словаре."""
    info = savings.get_account_info()
    assert "min_balance" in info
    assert "monthly_interest_rate" in info


def test_get_account_info_includes_savings_values(client):
    """Значения накопительных полей соответствуют атрибутам."""
    account = SavingsAccount(
        owner=client,
        currency=Currency.RUB,
        min_balance=Decimal("500"),
        monthly_interest_rate=Decimal("0.05"),
    )
    info = account.get_account_info()
    assert info["min_balance"] == Decimal("500")
    assert info["monthly_interest_rate"] == Decimal("0.05")


def test_str_contains_savings_type(savings):
    """В строке есть «Накопительный» — не путается с банковским."""
    assert "Накопительный" in str(savings)