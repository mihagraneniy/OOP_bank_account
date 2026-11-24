"""Тесты для InvestmentAccount.

Покрытие:
- инициализация (портфель пустой, все разрешённые активы по 0);
- invest() — happy path, накопление, ошибки (тип, знак, NaN/Inf, недостаток средств);
- portfolio — возвращает копию, а не ссылку;
- project_yearly_growth(growth_rates=None):
    * без аргумента → дефолтные ставки из GROWTH_RATES;
    * с custom → переопределение, fallback на дефолт, {} эквивалент None;
    * валидация ставки через _validate_attr: разрешён 0, запрещены
      отрицательные, не-Decimal, NaN, Infinity;
    * проекция — read-only, работает и на FROZEN / CLOSED.
"""

from decimal import Decimal
from datetime import date

import pytest

from bank_account.client import Client
from bank_account.enums import AssetType, Currency, AccountStatus
from bank_account.exceptions import (
    AccountClosedError,
    AccountFrozenError,
    InsufficientFundsError,
    InvalidOperationError,
)
from bank_account.investment_account import InvestmentAccount


# ---------- фикстуры ----------

@pytest.fixture
def client():
    return Client(
        name="Иван Иванов",
        birth_date=date(1990, 1, 1),
        phone="+79001234567",
    )


@pytest.fixture
def account(client):
    """Пустой инвестиционный счёт в рублях."""
    return InvestmentAccount(owner=client, currency=Currency.RUB)


@pytest.fixture
def funded_account(account):
    """Счёт с 1000 на балансе — для инвестирования."""
    account.deposit(Decimal("1000"))
    return account


# ---------- 1. Инициализация ----------

def test_new_account_balance_is_zero(account):
    """Новый счёт — нулевой баланс."""
    assert account.balance == Decimal("0")


def test_new_account_portfolio_contains_all_allowed_assets(account):
    """Портфель содержит все разрешённые активы с нулём."""
    portfolio = account.portfolio
    for asset in InvestmentAccount.ALLOWED_ASSETS:
        assert asset in portfolio
        assert portfolio[asset] == Decimal("0")


def test_portfolio_property_returns_copy(account):
    """Мутация полученного словаря не влияет на внутренний портфель."""
    external = account.portfolio
    external[AssetType.STOCKS] = Decimal("999")
    assert account.portfolio[AssetType.STOCKS] == Decimal("0")


# ---------- 2. invest() — happy path ----------

def test_invest_stocks_reduces_balance(funded_account):
    """Инвестирование уменьшает баланс на сумму вложения."""
    funded_account.invest(AssetType.STOCKS, Decimal("300"))
    assert funded_account.balance == Decimal("700")


def test_invest_increases_portfolio(funded_account):
    """Портфель по выбранному активу увеличивается."""
    funded_account.invest(AssetType.STOCKS, Decimal("300"))
    assert funded_account.portfolio[AssetType.STOCKS] == Decimal("300")


def test_invest_multiple_assets(funded_account):
    """Разные активы копятся независимо."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    funded_account.invest(AssetType.BONDS, Decimal("200"))
    funded_account.invest(AssetType.ETF, Decimal("300"))

    portfolio = funded_account.portfolio
    assert portfolio[AssetType.STOCKS] == Decimal("100")
    assert portfolio[AssetType.BONDS] == Decimal("200")
    assert portfolio[AssetType.ETF] == Decimal("300")
    assert funded_account.balance == Decimal("400")


def test_invest_same_asset_accumulates(funded_account):
    """Повторное вложение в тот же актив суммируется."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    funded_account.invest(AssetType.STOCKS, Decimal("150"))
    assert funded_account.portfolio[AssetType.STOCKS] == Decimal("250")


# ---------- 3. invest() — ошибки: сумма ----------

def test_invest_insufficient_funds_raises(funded_account):
    """Сумма больше баланса → InsufficientFundsError."""
    with pytest.raises(InsufficientFundsError):
        funded_account.invest(AssetType.STOCKS, Decimal("1500"))


def test_invest_insufficient_funds_preserves_state(funded_account):
    """При недостатке средств ни баланс, ни портфель не меняются."""
    with pytest.raises(InsufficientFundsError):
        funded_account.invest(AssetType.STOCKS, Decimal("1500"))
    assert funded_account.balance == Decimal("1000")
    assert funded_account.portfolio[AssetType.STOCKS] == Decimal("0")


@pytest.mark.parametrize("bad_amount", [
    Decimal("0"),
    Decimal("-100"),
    500.0,
    "500",
    500,
    Decimal("NaN"),
    Decimal("Infinity"),
], ids=["zero", "negative", "float", "str", "int", "nan", "inf"])
def test_invest_invalid_amount_raises(funded_account, bad_amount):
    """Некорректная сумма → InvalidOperationError."""
    with pytest.raises(InvalidOperationError):
        funded_account.invest(AssetType.STOCKS, bad_amount)


@pytest.mark.parametrize("bad_amount", [
    Decimal("0"),
    Decimal("-100"),
    500.0,
    "500",
    500,
    Decimal("NaN"),
    Decimal("Infinity"),
], ids=["zero", "negative", "float", "str", "int", "nan", "inf"])
def test_invest_invalid_amount_preserves_state(funded_account, bad_amount):
    """После ошибки баланс и портфель не тронуты."""
    with pytest.raises(InvalidOperationError):
        funded_account.invest(AssetType.STOCKS, bad_amount)
    assert funded_account.balance == Decimal("1000")
    assert funded_account.portfolio[AssetType.STOCKS] == Decimal("0")


# ---------- 4. invest() — ошибки: тип актива ----------

@pytest.mark.parametrize("bad_asset", [
    "STOCKS",
    "UNKNOWN",
    None,
    123,
], ids=["str-stocks", "str-unknown", "none", "int"])
def test_invest_invalid_asset_raises(funded_account, bad_asset):
    """Недопустимый тип актива → InvalidOperationError."""
    with pytest.raises(InvalidOperationError):
        funded_account.invest(bad_asset, Decimal("100"))


def test_invest_invalid_asset_preserves_state(funded_account):
    """При недопустимом активе ничего не меняется."""
    with pytest.raises(InvalidOperationError):
        funded_account.invest("STOCKS", Decimal("100"))
    assert funded_account.balance == Decimal("1000")
    assert all(v == Decimal("0") for v in funded_account.portfolio.values())


# ---------- 5. project_yearly_growth() — без аргумента ----------

def test_project_empty_portfolio_returns_zero(account):
    """Пустой портфель без аргумента → 0.00."""
    assert account.project_yearly_growth() == Decimal("0.00")


def test_project_single_asset_default_rate(funded_account):
    """100 STOCKS × 10% = 10.00 (ставка из GROWTH_RATES)."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    assert funded_account.project_yearly_growth() == Decimal("10.00")


def test_project_multiple_assets_default_rates(funded_account):
    """100×0.10 + 100×0.04 + 100×0.07 = 21.00."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    funded_account.invest(AssetType.BONDS, Decimal("100"))
    funded_account.invest(AssetType.ETF, Decimal("100"))
    assert funded_account.project_yearly_growth() == Decimal("21.00")


# ---------- 6. project_yearly_growth(custom) — кастомные ставки ----------

def test_project_custom_growth_rates(funded_account):
    """Кастомные ставки переопределяют дефолтные."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    custom = {AssetType.STOCKS: Decimal("0.20")}
    assert funded_account.project_yearly_growth(custom) == Decimal("20.00")


def test_project_partial_custom_rates_falls_back_to_default(funded_account):
    """Кастом задаёт только STOCKS, BONDS берёт дефолт.

    STOCKS: 100 × 0.20 = 20.00
    BONDS:  100 × 0.04 = 4.00   (дефолт через .get)
    Итого: 24.00
    """
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    funded_account.invest(AssetType.BONDS, Decimal("100"))
    custom = {AssetType.STOCKS: Decimal("0.20")}
    assert funded_account.project_yearly_growth(custom) == Decimal("24.00")


def test_project_empty_custom_dict_uses_defaults(funded_account):
    """Пустой dict эквивалентен None: .get(asset, GROWTH_RATES[asset])."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    assert funded_account.project_yearly_growth({}) == Decimal("10.00")


def test_project_zero_rate_allowed(funded_account):
    """rate=0 допустим — _validate_attr использует strict=False.

    100 × 0 = 0.00 — проекция «актив не растёт» валидна.
    """
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    assert funded_account.project_yearly_growth(
        {AssetType.STOCKS: Decimal("0")}
    ) == Decimal("0.00")


def test_project_rounds_half_up(funded_account):
    """1.05 × 0.10 = 0.105 → ROUND_HALF_UP → 0.11."""
    funded_account.invest(AssetType.STOCKS, Decimal("1.05"))
    assert funded_account.project_yearly_growth() == Decimal("0.11")


# ---------- 7. project_yearly_growth() — ошибки ----------

def test_project_invalid_asset_in_custom_raises(funded_account):
    """Недопустимый ключ в custom → InvalidOperationError."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    with pytest.raises(InvalidOperationError):
        funded_account.project_yearly_growth({"UNKNOWN": Decimal("0.10")})


@pytest.mark.parametrize("bad_rate", [
    Decimal("-0.1"),
    0.1,
    "0.1",
    1,
    Decimal("NaN"),
    Decimal("Infinity"),
], ids=["negative", "float", "str", "int", "nan", "inf"])
def test_project_invalid_rate_raises(funded_account, bad_rate):
    """Некорректная ставка → InvalidOperationError (через _validate_attr)."""
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    with pytest.raises(InvalidOperationError):
        funded_account.project_yearly_growth({AssetType.STOCKS: bad_rate})


# ---------- 8. Статусы FROZEN / CLOSED ----------

@pytest.mark.parametrize("status,exc", [
    (AccountStatus.FROZEN, AccountFrozenError),
    (AccountStatus.CLOSED, AccountClosedError),
], ids=["frozen", "closed"])
def test_invest_on_blocked_account_raises(funded_account, status, exc):
    """FROZEN / CLOSED не дают инвестировать (деньги не двигаются)."""
    funded_account._status = status
    with pytest.raises(exc):
        funded_account.invest(AssetType.STOCKS, Decimal("100"))


@pytest.mark.parametrize("status", [
    AccountStatus.FROZEN,
    AccountStatus.CLOSED,
], ids=["frozen", "closed"])
def test_invest_on_blocked_account_preserves_state(funded_account, status):
    """После отказа баланс и портфель не тронуты."""
    funded_account._status = status
    with pytest.raises((AccountFrozenError, AccountClosedError)):
        funded_account.invest(AssetType.STOCKS, Decimal("100"))
    assert funded_account.balance == Decimal("1000")
    assert funded_account.portfolio[AssetType.STOCKS] == Decimal("0")


@pytest.mark.parametrize("status", [
    AccountStatus.FROZEN,
    AccountStatus.CLOSED,
], ids=["frozen", "closed"])
def test_project_on_blocked_account_works(funded_account, status):
    """На FROZEN/CLOSED проекция считается.

    project_yearly_growth использует _validate_attr (без _check_status),
    потому что это read-only операция — она не двигает деньги.
    """
    funded_account.invest(AssetType.STOCKS, Decimal("100"))
    funded_account._status = status
    assert funded_account.project_yearly_growth() == Decimal("10.00")