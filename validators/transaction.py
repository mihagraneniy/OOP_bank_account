from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import TYPE_CHECKING

from enums.enums import TransactionType, TransactionStatus, Currency
from exceptions.exceptions import InvalidOperationError
from validators.base import BaseValidator

if TYPE_CHECKING:
    from bank_account.bank_account import BankAccount


class TransactionValidator:
    """Валидаторы для транзакций."""

    @staticmethod
    def validate_amount_and_fee(amount: Decimal, fee: Decimal) -> None:
        """Валидация суммы и комиссии транзакции."""
        BaseValidator.validate_amount(
            amount, "Сумма транзакции", strict=True
        )
        BaseValidator.validate_amount(
            fee, "Комиссия", strict=False
        )

        if fee > amount:
            raise InvalidOperationError(
                f"Комиссия ({fee}) не может превышать "
                f"сумму транзакции ({amount})"
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
            if not sender or not receiver:
                raise InvalidOperationError(
                    "Для внутреннего перевода обязательны оба счета"
                )

        elif transaction_type == TransactionType.DEPOSIT:
            if not receiver:
                raise InvalidOperationError(
                    "Для пополнения обязателен receiver"
                )

        elif transaction_type == TransactionType.WITHDRAWAL:
            if not sender:
                raise InvalidOperationError(
                    "Для снятия обязателен sender"
                )

        elif transaction_type == TransactionType.EXTERNAL_TRANSFER:
            if not sender or not receiver:
                raise InvalidOperationError(
                    "Для внешнего перевода обязательны оба счета"
                )

    @staticmethod
    def validate_bank_details(
        transaction_type: TransactionType,
        sender_bank: str | None,
        receiver_bank: str | None,
        sender_account_number: str | None,
        receiver_account_number: str | None
    ) -> None:
        """Проверка реквизитов для внешних переводов."""

        if transaction_type == TransactionType.EXTERNAL_TRANSFER:
            if not all([
                sender_bank,
                receiver_bank,
                sender_account_number,
                receiver_account_number
            ]):
                raise InvalidOperationError(
                    "Для внешнего перевода обязательны реквизиты "
                    "банков и номера счетов"
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
            if account is not None and account.currency != transaction_currency:
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

                if value < created_at:
                    raise InvalidOperationError(
                        f"{field_name} не может быть раньше created_at"
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

        if status.is_terminal and processed_at is None:
            raise InvalidOperationError(
                f"Для терминального статуса ({status.code}) "
                f"обязательно поле processed_at"
            )

        if (
            processed_at is not None
            and status in (
                TransactionStatus.PENDING,
                TransactionStatus.SCHEDULED,
                TransactionStatus.PROCESSING
            )
        ):
            raise InvalidOperationError(
                "processed_at не может быть установлен "
                "для незавершенного статуса"
            )
