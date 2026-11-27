import functools
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from client.client import Client

from bank_account.bank_account import BankAccount
from bank_account.savings_account import SavingsAccount
from bank_account.investment_account import InvestmentAccount
from bank_account.premium_account import PremiumAccount

from enums.enums import (
    ClientStatus,
    Currency,
    AccountStatus,
    AccountType,
    SuspiciousEventType,
)

from exceptions.exceptions import (
    InvalidOperationError,
    AccountNotFoundError,
    AuthenticationError,
    ClientBlockedError,
    OperationTimeError,
)

from validators import BankValidator

from .security_config import SecurityConfig
from .suspicious_action import SuspiciousAction


class Bank:

    def __init__(self, name: str):
        BankValidator.validate_name(name)

        self.name = name

        self._security_config = SecurityConfig()

        self._clients: dict[UUID, Client] = {}
        self._accounts: dict[UUID, BankAccount] = {}
        self._login_attempts: dict[UUID, int] = {}
        self._suspicious_actions: list[SuspiciousAction] = []

    @property
    def accounts(self):
        return self._accounts.copy()

    @property
    def clients(self):
        return self._clients.copy()

    @property
    def security_config(self):
        return self._security_config

    @staticmethod
    def operation_time_guard(method):
        """Блокирует команду банка в запрещённое время."""

        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            config = self.security_config
            now = datetime.now()

            if config.is_night_time(now):
                raise OperationTimeError(
                    f"Операция '{method.__name__}' недоступна в ночное время "
                    f"({config.night_start_hour:02d}:00-"
                    f"{config.night_end_hour:02d}:00), "
                    f"сейчас {now.strftime('%H:%M')}"
                )

            return method(self, *args, **kwargs)

        return wrapper

    @operation_time_guard
    def add_client(self, client: Client) -> None:
        BankValidator.validate_client(
            client,
            "Для регистрации необходимо передать объект Client"
        )

        if client.id in self._clients:
            raise InvalidOperationError(
                f"Клиент с ID {client.id} уже зарегистрирован"
            )

        BankValidator.validate_client_status(
            client.status,
            "Нельзя зарегистрировать неактивного клиента"
        )

        self._clients[client.id] = client
        self._login_attempts[client.id] = 0

    @operation_time_guard
    def open_account(
        self,
        client: Client,
        account_type: AccountType,
        currency: Currency,
        **kwargs
    ):
        BankValidator.validate_client(
            client,
            "Необходимо передать объект Client"
        )

        BankValidator.validate_account_type(account_type)
        BankValidator.validate_currency(currency)

        if client.id not in self._clients:
            raise InvalidOperationError(
                "Клиент не зарегистрирован в банке"
            )

        registered_client = self._clients[client.id]

        BankValidator.validate_client_status(
            registered_client.status,
            "Нельзя открыть счёт неактивному клиенту"
        )

        if account_type == AccountType.DEBET:
            account = BankAccount(
                registered_client,
                currency
            )

        elif account_type == AccountType.INVESTMENT:
            account = InvestmentAccount(
                registered_client,
                currency
            )

        elif account_type == AccountType.SAVING:
            BankValidator.validate_account_params(
                account_type,
                kwargs
            )

            account = SavingsAccount(
                registered_client,
                currency,
                min_balance=kwargs["min_balance"],
                monthly_interest_rate=kwargs["monthly_interest_rate"],
            )

        elif account_type == AccountType.PREMIUM:
            BankValidator.validate_account_params(
                account_type,
                kwargs
            )

            account = PremiumAccount(
                registered_client,
                currency,
                max_withdrawal=kwargs["max_withdrawal"],
                overdraft_limit=kwargs["overdraft_limit"],
                fixed_fee=kwargs["fixed_fee"],
            )

        else:
            raise InvalidOperationError(
                "Неизвестный тип счёта"
            )

        self._accounts[account.id] = account
        registered_client.accounts.append(account.id)

        return account

    @operation_time_guard
    def close_account(self, account_id: UUID) -> bool:
        BankValidator.validate_uuid(
            account_id,
            "Некорректный ID счёта"
        )

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )

        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError(
                "Нельзя закрыть уже закрытый счёт!"
            )

        if account.balance != Decimal("0"):
            raise InvalidOperationError(
                "Нельзя закрыть счёт с ненулевым балансом! "
                "Требуется скорректировать баланс повторить попытку"
            )

        client = account.owner

        if account_id not in client.accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден У клиента {client}"
            )

        account.change_account_status(AccountStatus.CLOSED)

        return True

    @operation_time_guard
    def freeze_account(self, account_id: UUID) -> bool:
        BankValidator.validate_uuid(
            account_id,
            "Некорректный ID счёта"
        )

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )

        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError(
                "Нельзя заморозить закрытый счёт"
            )

        if account.status == AccountStatus.FROZEN:
            return False

        account.change_account_status(AccountStatus.FROZEN)

        return True

    @operation_time_guard
    def unfreeze_account(self, account_id: UUID) -> bool:
        BankValidator.validate_uuid(
            account_id,
            "Некорректный ID счёта"
        )

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )

        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError(
                "Нельзя разморозить закрытый счёт"
            )

        if account.status == AccountStatus.ACTIVE:
            return False

        account.change_account_status(AccountStatus.ACTIVE)

        return True

    def _log_suspicious_action(
        self,
        event_type: SuspiciousEventType,
        *,
        client_id: UUID | None = None,
        account_id: UUID | None = None,
        details: dict | None = None,
    ) -> SuspiciousAction:

        action = SuspiciousAction(
            event_type=event_type,
            client_id=client_id,
            account_id=account_id,
            details=details or {},
        )

        self._suspicious_actions.append(action)

        return action

    @operation_time_guard
    def authenticate_client(
        self,
        client_id: UUID,
        pin: str
    ) -> bool:

        BankValidator.validate_authentication_id(client_id)
        BankValidator.validate_pin(pin)

        client = self._clients.get(client_id)

        if client is None:
            raise AuthenticationError(
                f"Клиент с ID {client_id} не найден"
            )

        if client.status != ClientStatus.ACTIVE:
            raise AuthenticationError(
                "Клиент не активен (заблокирован/удален)"
            )

        max_attempts = self._security_config.max_login_attempts

        if client.pin_code != pin:
            attempt = self._login_attempts.get(client_id, 0) + 1
            self._login_attempts[client_id] = attempt

            self._log_suspicious_action(
                SuspiciousEventType.FAILED_LOGIN,
                client_id=client_id,
                details={"attempt": attempt},
            )

            if attempt >= max_attempts:
                client.status = ClientStatus.BLOCKED

                self._log_suspicious_action(
                    SuspiciousEventType.CLIENT_BLOCKED,
                    client_id=client_id,
                    details={"attempts_total": attempt},
                )

                raise ClientBlockedError(
                    f"Клиент заблокирован после {max_attempts} "
                    f"неудачных попыток входа"
                )

            remaining = max_attempts - attempt

            raise AuthenticationError(
                f"Неверный PIN. Осталось попыток: {remaining}"
            )

        self._login_attempts[client_id] = 0

        return True

    def search_accounts(
        self,
        *,
        client_id: UUID | None = None,
        account_type: AccountType | None = None,
        status: AccountStatus | None = None,
        currency: Currency | None = None,
    ) -> list[BankAccount]:
        """
        Возвращает счета, удовлетворяющие всем заданным фильтрам.
        Без фильтров возвращает все открытые счета.
        """

        BankValidator.validate_search_filters(
            client_id=client_id,
            account_type=account_type,
            status=status,
            currency=currency,
        )

        no_filters = (
            client_id is None
            and account_type is None
            and status is None
            and currency is None
        )

        result: list[BankAccount] = []

        for account in self._accounts.values():

            if no_filters and account.status == AccountStatus.CLOSED:
                continue

            if (
                client_id is not None
                and account.owner.id != client_id
            ):
                continue

            if (
                account_type is not None
                and account.account_type != account_type
            ):
                continue

            if (
                status is not None
                and account.status != status
            ):
                continue

            if (
                currency is not None
                and account.currency != currency
            ):
                continue

            result.append(account)

        return result

    def get_total_balance(self) -> dict[Currency, Decimal]:
        """Суммирует балансы счетов по валютам."""

        totals: dict[Currency, Decimal] = {}

        for account in self._accounts.values():

            if account.status == AccountStatus.CLOSED:
                continue

            current = totals.get(
                account.currency,
                Decimal("0")
            )

            totals[account.currency] = current + account.balance

        return totals

    def get_clients_ranking(
        self
    ) -> dict[Currency, list[tuple[Client, Decimal]]]:
        """
        Рейтинг клиентов по суммарному балансу
        отдельно по каждой валюте.
        """

        buckets: dict[Currency, dict[UUID, list]] = {}

        for account in self._accounts.values():

            if account.status == AccountStatus.CLOSED:
                continue

            currency_bucket = buckets.setdefault(
                account.currency,
                {}
            )

            row = currency_bucket.setdefault(
                account.owner.id,
                [account.owner, Decimal("0")]
            )

            row[1] += account.balance

        ranking: dict[Currency, list[tuple[Client, Decimal]]] = {}

        for currency, rows in buckets.items():

            ordered = sorted(
                rows.values(),
                key=lambda row: row[1],
                reverse=True
            )

            ranking[currency] = [
                (client, total)
                for client, total in ordered
            ]

        return ranking