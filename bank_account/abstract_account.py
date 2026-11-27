
from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Dict

from enums.enums import AccountStatus
from validators import BaseValidator


class AbstractAccount(ABC):

    def __init__(
        self,
        owner,
        account_id: UUID | None = None
    ) -> None:
        if account_id is not None:
            BaseValidator.validate_uuid(account_id, "ID счёта")

        self._id = account_id if account_id is not None else uuid4()
        self._balance = Decimal("0")
        self._status = AccountStatus.ACTIVE
        self.owner = owner

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def balance(self) -> Decimal:
        return self._balance

    @property
    def status(self) -> AccountStatus:
        return self._status

    @abstractmethod
    def deposit(self, amount: Decimal) -> None:
        """Пополнение счёта."""

    @abstractmethod
    def withdraw(self, amount: Decimal) -> None:
        """Снятие средств со счёта."""

    @abstractmethod
    def get_account_info(self) -> Dict:
        """Получение информации о счёте."""
