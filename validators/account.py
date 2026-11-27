
from uuid import UUID

from enums.enums import Currency, AccountStatus
from exceptions.exceptions import (
    InvalidOperationError,
    AccountClosedError,
    AccountFrozenError
)


class AccountValidator:
    """Валидаторы для банковских счетов."""

    @staticmethod
    def validate_currency(
        currency: Currency,
        allowed_currencies: tuple[Currency, ...]
    ) -> None:
        """Проверяет допустимость валюты."""

        if not isinstance(currency, Currency):
            raise InvalidOperationError(
                f"Валюта должна иметь тип Currency, "
                f"получен тип {type(currency).__name__}"
            )

        if currency not in allowed_currencies:
            allowed_str = ", ".join(
                c.value for c in allowed_currencies
            )

            raise InvalidOperationError(
                f"Недопустимая валюта {currency.value}. "
                f"Поддерживаемые валюты: {allowed_str}"
            )

    @staticmethod
    def validate_account_status(
        status: AccountStatus,
        account_id: UUID | None = None
    ) -> None:
        """Проверяет статус счёта перед операцией."""

        if status == AccountStatus.ACTIVE:
            return

        if status == AccountStatus.FROZEN:
            raise AccountFrozenError(
                f"Счёт {account_id} заморожен"
                if account_id is not None
                else "Счёт заморожен"
            )

        if status == AccountStatus.CLOSED:
            raise AccountClosedError(
                f"Счёт {account_id} закрыт"
                if account_id is not None
                else "Счёт закрыт"
            )

        raise InvalidOperationError(
            f"Неизвестный статус счёта: {status!r}"
        )