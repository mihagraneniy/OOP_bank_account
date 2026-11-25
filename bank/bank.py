from client.client import Client
from bank_account.bank_account import BankAccount
from bank_account.investment_account import InvestmentAccount
from bank_account.premium_account import PremiumAccount
from enums.enums import ClientStatus, Currency, AccountStatus
from exceptions.exceptions import InvalidOperationError


class Bank:

    def __init__(self, name: str):
        if not isinstance(name, str) or not name.strip():
            raise InvalidOperationError(
                "Название банка должно быть непустой строкой"
            )

        self.name = name

        self._clients = {}
        self._accounts = {}

        self._login_attempts = {}
        self._suspicious_actions = []

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