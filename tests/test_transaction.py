
# tests/test_transaction.py

from datetime import datetime, timedelta
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


@pytest.fixture
def account(client):
    """Банковский счёт в рублях."""
    return BankAccount(
        owner=client,
        currency=Currency.RUB,
    )


@pytest.fixture
def second_account(make_client):
    """Второй счёт другого клиента."""
    owner = make_client(
        name="Пётр Петров",
        email="petr@example.com",
        phone="+79990001123",
    )
    return BankAccount(
        owner=owner,
        currency=Currency.RUB,
    )


# ---------------------------------------------------------
# 1. Создание транзакций и валидация полей
# ---------------------------------------------------------

def test_create_deposit_transaction(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("1000.00"),
        currency=Currency.RUB,
        receiver=account,
    )

    assert transaction.transaction_type == TransactionType.DEPOSIT
    assert transaction.amount == Decimal("1000.00")
    assert transaction.currency == Currency.RUB
    assert transaction.receiver is account
    assert transaction.status == TransactionStatus.PENDING
    assert transaction.fee == Decimal("0")


def test_create_withdrawal_transaction(account):
    transaction = Transaction(
        transaction_type=TransactionType.WITHDRAWAL,
        amount=Decimal("500.00"),
        currency=Currency.RUB,
        sender=account,
    )

    assert transaction.sender is account
    assert transaction.receiver is None


def test_create_internal_transfer(account, second_account):
    transaction = Transaction(
        transaction_type=TransactionType.INTERNAL_TRANSFER,
        amount=Decimal("250.00"),
        currency=Currency.RUB,
        sender=account,
        receiver=second_account,
    )

    assert transaction.sender is account
    assert transaction.receiver is second_account


def test_create_outgoing_external_transfer(account):
    transaction = Transaction(
        transaction_type=TransactionType.EXTERNAL_TRANSFER,
        amount=Decimal("750.00"),
        currency=Currency.RUB,
        sender=account,
        receiver_bank="Другой банк",
        receiver_account_number="12345678901234567890",
    )

    assert transaction.sender is account
    assert transaction.receiver is None
    assert transaction.receiver_bank == "Другой банк"


def test_create_incoming_external_transfer(account):
    transaction = Transaction(
        transaction_type=TransactionType.EXTERNAL_TRANSFER,
        amount=Decimal("750.00"),
        currency=Currency.RUB,
        receiver=account,
        sender_bank="Другой банк",
        sender_account_number="98765432109876543210",
    )

    assert transaction.sender is None
    assert transaction.receiver is account


@pytest.mark.parametrize(
    "amount",
    [
        Decimal("0"),
        Decimal("-100"),
    ],
)
def test_transaction_rejects_non_positive_amount(account, amount):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            currency=Currency.RUB,
            receiver=account,
        )


def test_transaction_rejects_negative_fee(account):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            currency=Currency.RUB,
            receiver=account,
            fee=Decimal("-1"),
        )


def test_transaction_rejects_missing_required_account():
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            currency=Currency.RUB,
        )


def test_internal_transfer_requires_both_accounts(account):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.INTERNAL_TRANSFER,
            amount=Decimal("100"),
            currency=Currency.RUB,
            sender=account,
        )


def test_transaction_rejects_currency_mismatch(account):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            currency=Currency.USD,
            receiver=account,
        )


def test_external_transfer_requires_bank_details(account):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.EXTERNAL_TRANSFER,
            amount=Decimal("100"),
            currency=Currency.RUB,
            sender=account,
        )


def test_scheduled_transaction_requires_scheduled_at(account):
    with pytest.raises(InvalidOperationError):
        Transaction(
            transaction_type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            currency=Currency.RUB,
            receiver=account,
            status=TransactionStatus.SCHEDULED,
        )


# ---------------------------------------------------------
# 2. Успешные переходы между статусами
# ---------------------------------------------------------

def test_pending_transaction_can_be_processed(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.mark_processing()

    assert transaction.status == TransactionStatus.PROCESSING


def test_processing_transaction_can_be_completed(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.mark_processing()
    transaction.mark_completed()

    assert transaction.status == TransactionStatus.COMPLETED
    assert transaction.processed_at is not None


def test_processing_transaction_can_be_failed(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.mark_processing()
    transaction.mark_failed("Ошибка обработки")

    assert transaction.status == TransactionStatus.FAILED
    assert transaction.processed_at is not None
    assert transaction.reason == "Ошибка обработки"


def test_pending_transaction_can_be_cancelled(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.cancel()

    assert transaction.status == TransactionStatus.CANCELLED
    assert transaction.processed_at is not None


def test_scheduled_transaction_can_be_processed_after_scheduled_time(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
        status=TransactionStatus.SCHEDULED,
        scheduled_at=datetime.now() - timedelta(minutes=1),
    )

    transaction.mark_processing()

    assert transaction.status == TransactionStatus.PROCESSING


# ---------------------------------------------------------
# 3. Запрещённые переходы и некорректные данные
# ---------------------------------------------------------

def test_pending_transaction_cannot_be_completed_directly(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    with pytest.raises(TransactionStatusError):
        transaction.mark_completed()


def test_pending_transaction_cannot_be_marked_failed_directly(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    with pytest.raises(TransactionStatusError):
        transaction.mark_failed("Ошибка")


def test_completed_transaction_cannot_be_cancelled(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.mark_processing()
    transaction.mark_completed()

    with pytest.raises(TransactionStatusError):
        transaction.cancel()


def test_cancelled_transaction_cannot_be_processed(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.cancel()

    with pytest.raises(TransactionStatusError):
        transaction.mark_processing()


def test_scheduled_transaction_cannot_be_processed_early(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
        status=TransactionStatus.SCHEDULED,
        scheduled_at=datetime.now() + timedelta(hours=1),
    )

    with pytest.raises(TransactionStatusError):
        transaction.mark_processing()


def test_failed_transaction_cannot_be_completed_again(account):
    transaction = Transaction(
        transaction_type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency=Currency.RUB,
        receiver=account,
    )

    transaction.mark_processing()
    transaction.mark_failed("Ошибка обработки")

    with pytest.raises(TransactionStatusError):
        transaction.mark_completed()
