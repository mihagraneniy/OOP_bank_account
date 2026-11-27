from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from enums.enums import (
    Currency,
    TransactionType,
    TransactionStatus,
    TransactionPriority
)
from bank.bank import Bank
from bank_account.bank_account import BankAccount
from validators import TransactionValidator, BaseValidator
from exceptions.exceptions import TransactionStatusError, InvalidOperationError

@dataclass
class Transaction:
    # Обязательные поля:
    transaction_type: TransactionType
    amount: Decimal
    currency: Currency

    sender: BankAccount | None = None
    receiver: BankAccount | None = None

    sender_bank: str | None = None
    receiver_bank: str | None = None
    sender_account_number: str | None = None
    receiver_account_number: str | None = None

    # Поля со значениями по умолчанию:
    id: UUID = field(default_factory=uuid4)
    fee: Decimal = Decimal("0")
    status: TransactionStatus = TransactionStatus.PENDING
    priority: TransactionPriority = TransactionPriority.NORMAL
    reason: str | None = None
    comment: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: datetime | None = None
    processed_at: datetime | None = None


    def __post_init__(self) -> None:
        """Валидация транзакции через внешние валидаторы."""

        TransactionValidator.validate_types(
           transaction_type=self.transaction_type,
            currency=self.currency,
            status= self.status,
            priority=self.priority,
        )

        TransactionValidator.validate_amount_and_fee(
            self.amount, self.fee
        )

        TransactionValidator.validate_accounts_by_type(
            self.transaction_type, self.sender, self.receiver
        )

        TransactionValidator.validate_bank_details(
            self.transaction_type,
            self.sender,
            self.receiver,
            self.sender_bank,
            self.receiver_bank,
            self.sender_account_number,
            self.receiver_account_number,
        )

        TransactionValidator.validate_currency_consistency(
            self.currency, self.sender, self.receiver
        )

        TransactionValidator.validate_temporal_fields(
            self.id,
            self.created_at,
            self.scheduled_at,
            self.processed_at,
        )

        TransactionValidator.validate_status_consistency(
            self.status,
            self.scheduled_at,
            self.processed_at,
        )



    # Жизненный цикл транзакции 
    def mark_processing(self) -> None:
        TransactionValidator.validate_status_transition(
            self.status,
            TransactionStatus.PROCESSING,
        )

        if self.status == TransactionStatus.SCHEDULED:
            if self.scheduled_at is None:
                raise TransactionStatusError(
                    "Для запланированной транзакции не указано время обработки"
                )

            now = datetime.now(tz=self.scheduled_at.tzinfo)

            if now < self.scheduled_at:
                raise TransactionStatusError(
                    "Время обработки транзакции ещё не наступило"
                )

        self.status = TransactionStatus.PROCESSING


    def mark_completed(self) -> None:
        """Успешно завершает транзакцию."""

        TransactionValidator.validate_status_transition(
            self.status,
            TransactionStatus.COMPLETED,
        )

        self.status = TransactionStatus.COMPLETED
        self.processed_at = datetime.now(
            tz=self.created_at.tzinfo
        )


    def mark_failed(self, reason: str) -> None:
        """Завершает транзакцию с ошибкой."""

        TransactionValidator.validate_status_transition(
            self.status,
            TransactionStatus.FAILED,
        )

        BaseValidator.validate_type(reason, str)

        if not reason.strip():
            raise InvalidOperationError(
                "Причина ошибки не может быть пустой"
            )

        self.status = TransactionStatus.FAILED
        self.reason = reason.strip()
        self.processed_at = datetime.now(
            tz=self.created_at.tzinfo
        )


    def cancel(self) -> None:
        TransactionValidator.validate_status_transition(
            self.status,
            TransactionStatus.CANCELLED,
        )

        self.status = TransactionStatus.CANCELLED
        self.processed_at = datetime.now(
            tz=self.created_at.tzinfo
        )