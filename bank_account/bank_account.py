from .abstract_account import AbstractAccount
from client.client import Client
from enums.enums import Currency, AccountStatus
from uuid import UUID
from decimal import Decimal
from exceptions.exceptions import (AccountClosedError, AccountFrozenError,
                        InsufficientFundsError, InvalidOperationError)

class BankAccount(AbstractAccount):
    
    ALLOWED_CURRENCIES = (
        Currency.RUB,
        Currency.CNY,
        Currency.EUR,
        Currency.KZT,
        Currency.USD
    )
    
    def __init__(self, owner: Client, currency: Currency, account_id: UUID | None = None):
        if not isinstance(owner, Client):
            raise InvalidOperationError(
                f"Владелец счёта должен быть объектом Client, "
                f"получен тип {type(owner).__name__}"
            )

        if account_id is not None and not isinstance(account_id, UUID):
            raise InvalidOperationError(
                f"ID счёта должен быть UUID, "
                f"получен тип {type(account_id).__name__}"
            )
        self._check_currency(currency)        
        
        super().__init__(owner, account_id)
        self.currency = currency
    
    def _check_currency(self, currency: Currency) -> None:
        if not isinstance(currency, Currency):
            raise InvalidOperationError(
                f"Валюта должна иметь тип Currency, "
                f"получен тип {type(currency).__name__}"
            )

        allowed_currencies_str = ", ".join(
            currency.value for currency in self.ALLOWED_CURRENCIES
        )

        if currency not in self.ALLOWED_CURRENCIES:
            raise InvalidOperationError(
                f"Недопустимая валюта {currency.value}. "
                f"Поддерживаемые валюты: {allowed_currencies_str}"
            )

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

    def _validate_attr(self, value):
        self._validate_decimal(value)
        self._validate_finite_amount(value)
        self._validate_non_negative_amount(value, strict=False)

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
        self._validate_withdrawal(amount)
        self._balance -= amount        

    def _validate_withdrawal(self, amount: Decimal):
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Сумма списания {amount} превышает "
                f"текущий баланс {self.balance} "
                f"на {amount - self.balance} {self.currency.value}"
            )

    def change_account_status(self, new_status):
        if not isinstance(new_status, AccountStatus):
            raise InvalidOperationError(f"Некорректный статус для установки, передан {new_status}")
        self._status = new_status
        
    def get_account_info(self):
        return {
            'id': str(self.id)[-4:],
            'type': type(self).__name__,
            'owner': self.owner.name,
            'status': self.status.value,
            'balance': self.balance,
            'currency': self.currency.value,
        }
    
    def __str__(self):
        pairs = ", \n".join(f"{k}:{v}" for k, v in self.get_account_info().items())
        return f"Банковский счет: ({pairs})" 