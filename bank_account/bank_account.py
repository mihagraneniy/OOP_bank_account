
from decimal import Decimal
from uuid import UUID

from .abstract_account import AbstractAccount
from client.client import Client
from enums.enums import Currency, AccountStatus
from exceptions.exceptions import InsufficientFundsError
from validators import BaseValidator, AccountValidator


class BankAccount(AbstractAccount):

    ALLOWED_CURRENCIES = (
        Currency.RUB,
        Currency.CNY,
        Currency.EUR,
        Currency.KZT,
        Currency.USD
    )

    def __init__(
        self,
        owner: Client,
        currency: Currency,
        account_id: UUID | None = None
    ) -> None:
        # Проверка владельца счёта
        BaseValidator.validate_type(
            owner,
            Client,
            "Владелец счёта"
        )

        # Проверка валюты
        AccountValidator.validate_currency(
            currency,
            self.ALLOWED_CURRENCIES
        )

        super().__init__(owner, account_id)

        self.currency = currency

    def _check_status(self) -> None:
        """Проверяет возможность выполнения операций со счётом."""
        AccountValidator.validate_account_status(self.status)

    def _validate_operation(
        self,
        amount: Decimal,
        *,
        strict: bool = True
    ) -> None:
        """Проверяет статус счёта и корректность суммы операции."""
        self._check_status()

        BaseValidator.validate_amount(
            amount,
            "Сумма",
            strict=strict
        )

    def deposit(self, amount: Decimal) -> None:
        """Пополняет баланс счёта."""
        self._validate_operation(amount, strict=True)

        self._balance += amount

    def withdraw(self, amount: Decimal) -> None:
        """Списывает средства со счёта."""
        self._validate_operation(amount, strict=True)

        self._validate_withdrawal(amount)

        self._balance -= amount

    def _validate_withdrawal(self, amount: Decimal) -> None:
        """Проверяет достаточность средств для списания."""
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Сумма списания {amount} превышает "
                f"текущий баланс {self.balance} "
                f"на {amount - self.balance} "
                f"{self.currency.value}"
            )

    def change_account_status(
        self,
        new_status: AccountStatus
    ) -> None:
        """Изменяет статус банковского счёта."""
        BaseValidator.validate_type(
            new_status,
            AccountStatus,
            "Статус"
        )

        self._status = new_status

    def get_account_info(self) -> dict:
        """Возвращает информацию о банковском счёте."""
        return {
            "id": str(self.id)[-4:],
            "type": type(self).__name__,
            "owner": self.owner.name,
            "status": self.status.value,
            "balance": self.balance,
            "currency": self.currency.value,
        }

    def __str__(self) -> str:
        pairs = ", \n".join(
            f"{key}: {value}"
            for key, value in self.get_account_info().items()
        )

        return f"Банковский счет: ({pairs})"