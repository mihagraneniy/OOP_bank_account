
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from enums.enums import (
    TransactionType,
    TransactionStatus,
    TransactionPriority,
    Currency,
)
from exceptions.exceptions import InvalidOperationError, TransactionStatusError
from validators.base import BaseValidator

if TYPE_CHECKING:
    from bank_account.bank_account import BankAccount


class TransactionValidator:
    """Валидаторы для транзакций."""

    @staticmethod
    def validate_types(
        transaction_type: TransactionType,
        currency: Currency,
        status: TransactionStatus,
        priority: TransactionPriority,
    ) -> None:
        """Проверка типов основных полей транзакции."""

        checks = (
            (transaction_type, TransactionType, "transaction_type"),
            (currency, Currency, "currency"),
            (status, TransactionStatus, "status"),
            (priority, TransactionPriority, "priority"),
        )

        for value, expected_type, field_name in checks:
            if not isinstance(value, expected_type):
                raise InvalidOperationError(
                    f"{field_name} должен быть {expected_type.__name__}"
                )

    @staticmethod
    def validate_amount_and_fee(
        amount: Decimal,
        fee: Decimal
    ) -> None:
        """Валидация суммы и комиссии транзакции."""

        BaseValidator.validate_amount(
            amount, "Сумма транзакции", strict=True
        )
        BaseValidator.validate_amount(
            fee, "Комиссия", strict=False
        )

    @staticmethod
    def validate_accounts_by_type(
        transaction_type: TransactionType,
        sender: BankAccount | None,
        receiver: BankAccount | None
    ) -> None:
        """Проверка наличия счетов в зависимости от типа транзакции."""

        from bank_account.bank_account import BankAccount

        for field_name, account in (
            ("sender", sender),
            ("receiver", receiver)
        ):
            if account is not None and not isinstance(account, BankAccount):
                raise InvalidOperationError(
                    f"{field_name} должен быть BankAccount или None, "
                    f"получен {type(account).__name__}"
                )

        if transaction_type == TransactionType.INTERNAL_TRANSFER:
            if sender is None or receiver is None:
                raise InvalidOperationError(
                    "Для внутреннего перевода обязательны оба счета"
                )

        elif transaction_type == TransactionType.DEPOSIT:
            if receiver is None:
                raise InvalidOperationError(
                    "Для пополнения обязателен receiver"
                )

        elif transaction_type == TransactionType.WITHDRAWAL:
            if sender is None:
                raise InvalidOperationError(
                    "Для снятия обязателен sender"
                )

        elif transaction_type == TransactionType.EXTERNAL_TRANSFER:
            # Исходящий перевод: наш счет -> внешний получатель.
            # Входящий перевод: внешний отправитель -> наш счет.
            if (sender is None and receiver is None) or (
                sender is not None and receiver is not None
            ):
                raise InvalidOperationError(
                    "Для внешнего перевода должен быть указан "
                    "ровно один внутренний счет: sender или receiver"
                )
        else:
            raise InvalidOperationError(
                f"Неизвестный тип транзакции: {transaction_type}"
            )

    @staticmethod
    def validate_bank_details(
        transaction_type: TransactionType,
        sender: BankAccount | None,
        receiver: BankAccount | None,
        sender_bank: str | None,
        receiver_bank: str | None,
        sender_account_number: str | None,
        receiver_account_number: str | None
    ) -> None:
        """Проверка реквизитов внешней стороны перевода."""

        if transaction_type != TransactionType.EXTERNAL_TRANSFER:
            return

        if sender is not None:
            # Исходящий перевод: внешний получатель.
            required_details = (
                ("receiver_bank", receiver_bank),
                ("receiver_account_number", receiver_account_number),
            )
        elif receiver is not None:
            # Входящий перевод: внешний отправитель.
            required_details = (
                ("sender_bank", sender_bank),
                ("sender_account_number", sender_account_number),
            )
        else:
            raise InvalidOperationError(
                "Для внешнего перевода должен быть указан внутренний счет"
            )

        for field_name, value in required_details:
            if not isinstance(value, str) or not value.strip():
                raise InvalidOperationError(
                    f"Для внешнего перевода обязательно поле {field_name}"
                )

    @staticmethod
    def validate_currency_consistency(
        transaction_currency: Currency,
        sender: BankAccount | None,
        receiver: BankAccount | None
    ) -> None:
        """Проверка совпадения валюты транзакции с валютой счетов."""

        for field_name, account in (
            ("sender", sender),
            ("receiver", receiver)
        ):
            if (
                account is not None
                and account.currency != transaction_currency
            ):
                raise InvalidOperationError(
                    f"Валюта {field_name} ({account.currency}) не совпадает "
                    f"с валютой транзакции ({transaction_currency})"
                )

    @staticmethod
    def validate_temporal_fields(
        id: UUID,
        created_at: datetime,
        scheduled_at: datetime | None,
        processed_at: datetime | None
    ) -> None:
        """Валидация UUID и временных полей."""

        BaseValidator.validate_uuid(id, "ID транзакции")
        BaseValidator.validate_datetime(created_at, "created_at")
        BaseValidator.validate_not_future(created_at, "created_at")

        for field_name, value in (
            ("scheduled_at", scheduled_at),
            ("processed_at", processed_at)
        ):
            if value is not None:
                BaseValidator.validate_datetime(
                    value, field_name, allow_none=True
                )

    @staticmethod
    def validate_status_consistency(
        status: TransactionStatus,
        scheduled_at: datetime | None,
        processed_at: datetime | None
    ) -> None:
        """Проверка согласованности статуса с временными полями."""

        if status == TransactionStatus.SCHEDULED and scheduled_at is None:
            raise InvalidOperationError(
                "Для статуса SCHEDULED обязательно поле scheduled_at"
            )

        terminal_statuses = (
            TransactionStatus.COMPLETED,
            TransactionStatus.FAILED,
            TransactionStatus.CANCELLED,
        )

        if status in terminal_statuses and processed_at is None:
            raise InvalidOperationError(
                f"Для терминального статуса ({status.name}) "
                f"обязательно поле processed_at"
            )

        if (
            processed_at is not None
            and status not in terminal_statuses
        ):
            raise InvalidOperationError(
                "processed_at не может быть установлен "
                "для незавершенного статуса"
            )
        if (
            status == TransactionStatus.PENDING
            and scheduled_at is not None
        ):
            raise InvalidOperationError(
                "Для статуса PENDING поле scheduled_at должно отсутствовать"
            )

    @staticmethod
    def validate_status_transition(
        current_status: TransactionStatus,
        new_status: TransactionStatus,
    ) -> None:
        """Проверка допустимости перехода между статусами."""

        allowed_transitions = {
            TransactionStatus.PENDING: {
                TransactionStatus.PROCESSING,
                TransactionStatus.CANCELLED,
            },
            TransactionStatus.SCHEDULED: {
                TransactionStatus.PROCESSING,
                TransactionStatus.CANCELLED,
            },
            TransactionStatus.PROCESSING: {
                TransactionStatus.COMPLETED,
                TransactionStatus.FAILED,
            },

        }

        if new_status not in allowed_transitions.get(current_status, set()):
            raise TransactionStatusError(
                f"Недопустимый переход из {current_status.name} "
                f"в {new_status.name}"
            )