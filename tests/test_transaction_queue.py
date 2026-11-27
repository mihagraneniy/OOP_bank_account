# tests/test_transaction_queue.py

from decimal import Decimal

import pytest

from bank_account.bank_account import BankAccount
from enums.enums import (
    Currency,
    TransactionType,
    TransactionStatus,
    TransactionPriority,
)
from exceptions.exceptions import (
    InvalidOperationError,
    TransactionStatusError,
)
from transaction.transaction import Transaction

# ⚠ поправь путь под свой проект:
from transaction.transaction_queue import TransactionQueue


# ---------------------------------------------------------
# Фикстуры и хелперы
# ---------------------------------------------------------

@pytest.fixture
def account(client):
    """Счёт в рублях для транзакций."""
    return BankAccount(owner=client, currency=Currency.RUB)


def make_tx(account, priority=TransactionPriority.NORMAL):
    """Валидная DEPOSIT-транзакция с заданным приоритетом."""
    return Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
        priority=priority,
    )


# ---------------------------------------------------------
# 1. add()
# ---------------------------------------------------------

def test_add_single_transaction(account):
    q = TransactionQueue()
    q.add(make_tx(account))
    assert len(q) == 1


def test_add_multiple_transactions(account):
    q = TransactionQueue()
    for _ in range(3):
        q.add(make_tx(account))
    assert len(q) == 3


def test_add_rejects_non_transaction():
    """validate_types(transaction=...) ловит не-Transaction."""
    q = TransactionQueue()
    with pytest.raises(InvalidOperationError):
        q.add("not-a-transaction")


def test_add_rejects_duplicate_id(account):
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    with pytest.raises(ValueError, match="уже находится в очереди"):
        q.add(tx)


def test_add_after_pop_allows_same_id_again(account):
    """После pop_next id удаляется из индекса → можно добавить повторно."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.pop_next()
    q.add(tx)              # не должно бросить ValueError
    assert len(q) == 1


# ---------------------------------------------------------
# 2. get_next()
# ---------------------------------------------------------

def test_get_next_empty_returns_none():
    assert TransactionQueue().get_next() is None


def test_get_next_returns_highest_priority(account):
    q = TransactionQueue()
    low = make_tx(account, TransactionPriority.LOW)
    normal = make_tx(account, TransactionPriority.NORMAL)
    high = make_tx(account, TransactionPriority.HIGH)
    q.add(low)
    q.add(normal)
    q.add(high)
    assert q.get_next() is high


def test_get_next_does_not_remove(account):
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.get_next()
    assert len(q) == 1


def test_get_next_fifo_for_same_priority(account):
    q = TransactionQueue()
    first = make_tx(account)
    second = make_tx(account)
    q.add(first)
    q.add(second)
    assert q.get_next() is first


def test_get_next_returns_cancelled_transaction(account):
    """⚠ Фиксируем текущее поведение: get_next пропускает CANCELLED
    """
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.cancel(tx.id)
    assert q.get_next() is not tx

def test_get_next_returns_transaction_not_tuple(account):
    """Регрессия: раньше возвращался (priority, counter, tx)."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    result = q.get_next()
    assert isinstance(result, Transaction)
    assert result is tx

# ---------------------------------------------------------
# 3. pop_next()
# ---------------------------------------------------------

def test_pop_next_empty_returns_none():
    assert TransactionQueue().pop_next() is None


def test_pop_next_returns_and_removes(account):
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    assert q.pop_next() is tx
    assert len(q) == 0


def test_pop_next_respects_priority(account):
    q = TransactionQueue()
    low = make_tx(account, TransactionPriority.LOW)
    high = make_tx(account, TransactionPriority.HIGH)
    q.add(low)
    q.add(high)
    assert q.pop_next() is high
    assert q.pop_next() is low


def test_pop_next_skips_cancelled_transactions(account):
    q = TransactionQueue()
    high = make_tx(account, TransactionPriority.HIGH)
    low = make_tx(account, TransactionPriority.LOW)
    q.add(high)
    q.add(low)
    q.cancel(high.id)

    assert q.pop_next() is low
    # обе записи уже вычищены из кучи (high — как cancelled)
    assert len(q) == 0
    assert q.pop_next() is None


def test_pop_next_removes_from_index(account):
    """Косвенно проверяем, что id удалён из _transactions после pop."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.pop_next()
    q.add(tx)              # ValueError не должно быть
    assert len(q) == 1


# ---------------------------------------------------------
# 4. cancel()
# ---------------------------------------------------------

def test_cancel_unknown_returns_false():
    q = TransactionQueue()
    assert q.cancel("unknown-id") is False


def test_cancel_known_sets_status(account):
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    assert q.cancel(tx.id) is True
    assert tx.status == TransactionStatus.CANCELLED


def test_cancel_twice_raises(account):
    """CANCELLED → CANCELLED запрещено → TransactionStatusError."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.cancel(tx.id)
    with pytest.raises(TransactionStatusError):
        q.cancel(tx.id)


def test_cancel_processing_raises(account):
    """PROCESSING → CANCELLED запрещено правилами переходов."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    tx.mark_processing()
    with pytest.raises(TransactionStatusError):
        q.cancel(tx.id)


# ---------------------------------------------------------
# 5. __len__
# ---------------------------------------------------------

def test_len_empty():
    assert len(TransactionQueue()) == 0


def test_len_counts_cancelled_until_popped(account):
    """Отменённые остаются в куче до pop_next → len их считает."""
    q = TransactionQueue()
    tx = make_tx(account)
    q.add(tx)
    q.cancel(tx.id)
    assert len(q) == 1
    q.pop_next()
    assert len(q) == 0


# ---------------------------------------------------------
# 6. Интеграция: порядок выборки
# ---------------------------------------------------------

def test_priority_order_high_normal_low(account):
    q = TransactionQueue()
    low = make_tx(account, TransactionPriority.LOW)
    normal = make_tx(account, TransactionPriority.NORMAL)
    high = make_tx(account, TransactionPriority.HIGH)
    q.add(low)
    q.add(normal)
    q.add(high)

    assert [q.pop_next() for _ in range(3)] == [high, normal, low]


def test_fifo_inside_same_priority(account):
    q = TransactionQueue()
    t1 = make_tx(account)
    t2 = make_tx(account)
    t3 = make_tx(account)
    q.add(t1)
    q.add(t2)
    q.add(t3)
    assert [q.pop_next() for _ in range(3)] == [t1, t2, t3]


def test_mixed_priorities_stable_order(account):
    """Внутри HIGH — FIFO, затем NORMAL, затем LOW."""
    q = TransactionQueue()
    h1 = make_tx(account, TransactionPriority.HIGH)
    l1 = make_tx(account, TransactionPriority.LOW)
    h2 = make_tx(account, TransactionPriority.HIGH)
    n1 = make_tx(account, TransactionPriority.NORMAL)
    q.add(h1)
    q.add(l1)
    q.add(h2)
    q.add(n1)

    assert [q.pop_next() for _ in range(4)] == [h1, h2, n1, l1]