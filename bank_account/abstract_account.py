from abc  import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Dict
from .enums import AccountStatus

class AbstractAccount(ABC):

    def __init__(self, owner, account_id: UUID | None  = None):
        self._id = account_id if account_id is not None else uuid4()  
        self._balance = Decimal("0")
        self._status = AccountStatus.ACTIVE
        self.owner = owner

    @property
    def id(self):
        return (str(self._id))[-4::]

    @property
    def balance(self):
        return self._balance

    @property
    def status(self):
        return self._status
   
    @abstractmethod
    def deposit(self, amount: Decimal) -> None:
        """ Пополнение — общая логика """
        pass

    @abstractmethod
    def withdraw(self, amount: Decimal) -> None:
        """ Снятие — общая логика """
        pass

    @abstractmethod
    def get_account_info(self) -> Dict:
        """ Доступный баланс — общая логика """
        pass