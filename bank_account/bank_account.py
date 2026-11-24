from .abstract_account import AbstractAccount
from .client import Client
from .enums import Currency, AccountStatus
from uuid import UUID
from decimal import Decimal
from .exceptions import (AccountClosedError, AccountFrozenError,
                        InsufficientFundsError, InvalidOperationError)

class BankAccount(AbstractAccount):
    def __init__(self, owner: Client, currency: Currency, account_id: UUID | None = None):
        super().__init__(owner, account_id)
        self.currency = currency
    
    def _check_status(self):
        if self.status == AccountStatus.ACTIVE:
            return True
        elif self.status == AccountStatus.FROZEN:
            raise AccountFrozenError(f"Счёт {self.id} заморожен") 
        elif self.status == AccountStatus.CLOSED:
            raise AccountClosedError(f"Счёт {self.id} закрыт")
        else:
            raise InvalidOperationError(f"Неизвестный статус счёта: {self.status!r}") 
    
    def _validate_decimal(self, amount:Decimal):
        if not isinstance(amount, Decimal):
            raise InvalidOperationError(
                f"Сумма должна быть типом - Decimal, получен тип - {type(amount).__name__}"
            ) 
           
    def _validate_finite_amount(self, amount:Decimal):
        if not amount.is_finite():
            raise InvalidOperationError(f"Сумма должна быть конечным числом, передано {amount}")

    def _validate_non_negative_amount(self, amount: Decimal, *, strict: bool = False):
        if strict:
            if amount <= 0:
                raise InvalidOperationError(
                    f"Сумма должна быть больше нуля, передано {amount}"
                )
        else:
            if amount < 0:
                raise InvalidOperationError(
                    f"Сумма должна быть неотрицательной, передано {amount}"
                )

    def _validate_operation(self, amount: Decimal, *, strict: bool = True):
        self._check_status()
        self._validate_decimal(amount)
        self._validate_finite_amount(amount)
        self._validate_non_negative_amount(amount, strict=strict)

    def deposit(self, amount:Decimal):
        self._validate_operation(amount, strict = True)
        self._balance += amount

    def withdraw(self, amount:Decimal):
        self._validate_operation(amount, strict = True)
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Сумма списания {amount} превышает текущий баланс {self.balance} на {amount - self.balance} {self.currency.value}"
            )
        self._balance -= amount        

    def get_account_info(self):
        return {
            'id': self.id,
            'type': type(self).__name__,
            'owner': self.owner.name,
            'status': self.status.value,
            'balance': self.balance,
            'currency': self.currency.value,
        }
    
    def __str__(self):
        pairs = ", \n".join(f"{k}:{v}" for k, v in self.get_account_info().items())
        return f"Банковский счет: ({pairs})" 