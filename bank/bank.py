from client.client import Client
from bank_account.bank_account import BankAccount
from bank_account.savings_account import SavingsAccount
from bank_account.investment_account import InvestmentAccount
from bank_account.premium_account import PremiumAccount
from enums.enums import ClientStatus, Currency, AccountStatus, AccountType
from exceptions.exceptions import InvalidOperationError, AccountNotFoundError, AuthenticationError, ClientBlockedError, OperationTimeError
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from .security_config import SecurityConfig
from .suspicious_action import SuspiciousAction
from enums.enums import SuspiciousEventType

import functools



class Bank:

    def __init__(self, name: str):
        if not isinstance(name, str) or not name.strip():
            raise InvalidOperationError(
                "Название банка должно быть непустой строкой"
            )

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
    
    def operation_time_guard(method):
        """Блокирует команду банка в запрещённое время из его security_config."""
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            config = self.security_config
            now = datetime.now()
            if config.is_night_time(now):
                raise OperationTimeError(
                    f"Операция '{method.__name__}' недоступна в ночное время "
                    f"({config.night_start_hour:02d}:00-{config.night_end_hour:02d}:00), "
                    f"сейчас {now.strftime('%H:%M')}"
                )
            return method(self, *args, **kwargs)
        return wrapper

    @operation_time_guard
    def add_client(self, client: Client) -> None:
        if not isinstance(client, Client):
            raise InvalidOperationError(
                "Для регистрации необходимо передать объект Client"
            )

        if client.id in self._clients:
            raise InvalidOperationError(
                f"Клиент с ID {client.id} уже зарегистрирован"
            )

        if client.status != ClientStatus.ACTIVE:
            raise InvalidOperationError(
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
        if not isinstance(client, Client):
            raise InvalidOperationError(
                "Необходимо передать объект Client"
            )

        if not isinstance(account_type, AccountType):
            raise InvalidOperationError("Некорректный тип счёта")

        if not isinstance(currency, Currency):
            raise InvalidOperationError("Некорректная валюта")

        if client.id not in self._clients:
            raise InvalidOperationError(
                "Клиент не зарегистрирован в банке"
            )

        registered_client = self._clients[client.id]

        if registered_client.status != ClientStatus.ACTIVE:
            raise InvalidOperationError(
                "Нельзя открыть счёт неактивному клиенту"
            )
        
        if account_type == AccountType.DEBET:
            account = BankAccount(registered_client, currency)

        elif account_type == AccountType.INVESTMENT:
            account = InvestmentAccount(registered_client, currency)
        
        elif account_type == AccountType.SAVING:
            
            required_params = {
                "min_balance",
                "monthly_interest_rate"
            }

            if not required_params.issubset(kwargs):
                raise InvalidOperationError(
                    "Для SavingsAccount необходимы "
                    "min_balance и monthly_interest_rate"
                )

            account = SavingsAccount(
                registered_client,
                currency,
                min_balance=kwargs["min_balance"],
                monthly_interest_rate=kwargs["monthly_interest_rate"],
            )

        elif account_type == AccountType.PREMIUM:
            required_params = {
                "max_withdrawal",
                "overdraft_limit",
                "fixed_fee"
            }

            if not required_params.issubset(kwargs):
                raise InvalidOperationError(
                    "Для PremiumAccount необходимы "
                    "max_withdrawal, overdraft_limit и fixed_fee"
                )

            account = PremiumAccount(
                registered_client,
                currency,
                max_withdrawal=kwargs["max_withdrawal"],
                overdraft_limit=kwargs["overdraft_limit"],
                fixed_fee=kwargs["fixed_fee"]
            )

        else:
            raise InvalidOperationError(
                "Неизвестный тип счёта"
            )

        self._accounts[account.id] = account
        registered_client.accounts.append(account.id)

        return account

    @operation_time_guard
    def close_account(self, account_id):
 
        if not isinstance(account_id, UUID):
            raise InvalidOperationError("Некорректный ID счёта")

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )
        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError("Нельзя закрыть уже закрытый счёт!")


        if account.balance != Decimal("0"): 
            raise InvalidOperationError("Нельзя закрыть счёт с ненулевым балансом! " \
                                        "Требуется скорректировать баланс повторить попытку") 
        
        client = account.owner

        if account_id not in client.accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден У клиента {client}"
            )
        account.change_account_status(AccountStatus.CLOSED)
        
        return True

    @operation_time_guard
    def freeze_account(self, account_id: UUID) -> bool:

        if not isinstance(account_id, UUID):
            raise InvalidOperationError("Некорректный ID счёта")

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )

        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError("Нельзя заморозить закрытый счёт")

        if account.status == AccountStatus.FROZEN:
            return False

        account.change_account_status(AccountStatus.FROZEN)
        return True

    @operation_time_guard
    def unfreeze_account(self, account_id: UUID) -> bool:

        if not isinstance(account_id, UUID):
            raise InvalidOperationError("Некорректный ID счёта")

        if account_id not in self._accounts:
            raise AccountNotFoundError(
                f"Счёт с ID {account_id} не найден"
            )

        account = self._accounts[account_id]

        if account.status == AccountStatus.CLOSED:
            raise InvalidOperationError("Нельзя разморозить закрытый счёт")

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
    def authenticate_client(self, client_id: UUID, pin: str) -> bool:

        if not isinstance(client_id, UUID):
            raise AuthenticationError("Некорректный ID клиента")

        if not isinstance(pin, str):
            raise AuthenticationError("PIN должен быть строкой")

        client = self._clients.get(client_id)
        if client is None:
            raise AuthenticationError(f"Клиент с ID {client_id} не найден")

        if client.status != ClientStatus.ACTIVE:
            raise AuthenticationError("Клиент не активен (заблокирован/удален)")

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

        # Успех — сбрасываем счётчик
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
        """Возвращает счета, удовлетворяющие одновременно всем заданным фильтрам.
        Без фильтров — все открытые счета (статус != CLOSED)
        """
        if client_id is not None and not isinstance(client_id, UUID):
            raise InvalidOperationError("Фильтр client_id должен быть UUID")
        if account_type is not None and not isinstance(account_type, AccountType):
            raise InvalidOperationError("Фильтр account_type должен быть AccountType")
        if status is not None and not isinstance(status, AccountStatus):
            raise InvalidOperationError("Фильтр status должен быть AccountStatus")
        if currency is not None and not isinstance(currency, Currency):
            raise InvalidOperationError("Фильтр currency должен быть Currency")

        no_filters = (
            client_id is None
            and account_type is None
            and status is None
            and currency is None
        )

        result: list[BankAccount] = []

        for account in self._accounts.values():
            # Закрытые счета скрываем если статус не запрошен явно
            if no_filters and account.status == AccountStatus.CLOSED:
                continue
            if client_id is not None and account.owner.id != client_id:
                continue
            if account_type is not None and account.account_type != account_type:
                continue
            if status is not None and account.status != status:
                continue
            if currency is not None and account.currency != currency:
                continue

            result.append(account)

        return result

    def get_total_balance(self) -> dict[Currency, Decimal]:
        """Суммирует балансы счетов по валютам."""
 
        totals: dict[Currency, Decimal] = {}

        for account in self._accounts.values():
            if account.status == AccountStatus.CLOSED:
                continue
            current = totals.get(account.currency, Decimal("0"))
            totals[account.currency] = current + account.balance

        return totals

    def get_clients_ranking(self) -> dict[Currency, list[tuple[Client, Decimal]]]:
        """ Рейтинг клиентов по суммарному балансу отдельно по каждой валюте. """
        
        # Фаза 1: накопление — валюта -> (id клиента -> [клиент, сумма])
        buckets: dict[Currency, dict[UUID, list]] = {}

        for account in self._accounts.values():
            if account.status == AccountStatus.CLOSED:
                continue
            currency_bucket = buckets.setdefault(account.currency, {})
            row = currency_bucket.setdefault(
                account.owner.id, [account.owner, Decimal("0")]
            )
            row[1] += account.balance

        # Фаза 2: сортировка клиентов внутри каждой валюты по убыванию суммы
        ranking: dict[Currency, list[tuple[Client, Decimal]]] = {}
        for currency, rows in buckets.items():
            ordered = sorted(rows.values(), key=lambda row: row[1], reverse=True)
            ranking[currency] = [(client, total) for client, total in ordered]

        return ranking