
from uuid import UUID

from enums.enums import (
    ClientStatus,
    AccountType,
    AccountStatus,
    Currency
)
from exceptions.exceptions import (
    InvalidOperationError,
    AuthenticationError
)


class BankValidator:
    """Валидаторы для операций банка."""

    @staticmethod
    def validate_name(name: str) -> None:
        """Проверяет название банка."""
        if not isinstance(name, str) or not name.strip():
            raise InvalidOperationError(
                "Название банка должно быть непустой строкой"
            )

    @staticmethod
    def validate_client(
        client,
        message="Для регистрации необходимо передать объект Client"
    ):
        from client.client import Client

        if not isinstance(client, Client):
            raise InvalidOperationError(message)

    @staticmethod
    def validate_client_status(
        status: ClientStatus,
        message: str
    ) -> None:
        """Проверяет активность клиента."""
        if status != ClientStatus.ACTIVE:
            raise InvalidOperationError(message)

    @staticmethod
    def validate_account_type(account_type: AccountType) -> None:
        """Проверяет тип банковского счёта."""
        if not isinstance(account_type, AccountType):
            raise InvalidOperationError("Некорректный тип счёта")

    @staticmethod
    def validate_currency(currency: Currency) -> None:
        """Проверяет тип валюты."""
        if not isinstance(currency, Currency):
            raise InvalidOperationError("Некорректная валюта")

    @staticmethod
    def validate_uuid(
        value: UUID,
        message: str = "Некорректный UUID"
    ) -> None:
        """Проверяет UUID."""
        if not isinstance(value, UUID):
            raise InvalidOperationError(message)

    @staticmethod
    def validate_account_params(
        account_type: AccountType,
        kwargs: dict
    ) -> None:
        """Проверяет обязательные параметры конкретного типа счёта."""

        required_params = {
            AccountType.SAVING: {
                "min_balance",
                "monthly_interest_rate"
            },
            AccountType.PREMIUM: {
                "max_withdrawal",
                "overdraft_limit",
                "fixed_fee"
            }
        }

        required = required_params.get(account_type)

        if required is None:
            return

        if not required.issubset(kwargs):
            if account_type == AccountType.SAVING:
                raise InvalidOperationError(
                    "Для SavingsAccount необходимы "
                    "min_balance и monthly_interest_rate"
                )

            if account_type == AccountType.PREMIUM:
                raise InvalidOperationError(
                    "Для PremiumAccount необходимы "
                    "max_withdrawal, overdraft_limit и fixed_fee"
                )

    @staticmethod
    def validate_authentication_id(client_id: UUID) -> None:
        """Проверяет ID клиента при аутентификации."""
        if not isinstance(client_id, UUID):
            raise AuthenticationError("Некорректный ID клиента")

    @staticmethod
    def validate_pin(pin: str) -> None:
        """Проверяет тип PIN-кода при аутентификации."""
        if not isinstance(pin, str):
            raise AuthenticationError("PIN должен быть строкой")

    @staticmethod
    def validate_search_filters(
        client_id: UUID | None = None,
        account_type: AccountType | None = None,
        status: AccountStatus | None = None,
        currency: Currency | None = None
    ) -> None:
        """Проверяет фильтры поиска счетов."""

        if client_id is not None and not isinstance(client_id, UUID):
            raise InvalidOperationError(
                "Фильтр client_id должен быть UUID"
            )

        if account_type is not None and not isinstance(
            account_type, AccountType
        ):
            raise InvalidOperationError(
                "Фильтр account_type должен быть AccountType"
            )

        if status is not None and not isinstance(status, AccountStatus):
            raise InvalidOperationError(
                "Фильтр status должен быть AccountStatus"
            )

        if currency is not None and not isinstance(currency, Currency):
            raise InvalidOperationError(
                "Фильтр currency должен быть Currency"
            )