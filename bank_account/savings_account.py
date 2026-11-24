from decimal import Decimal, ROUND_HALF_UP
from .bank_account import BankAccount
from .exceptions import InvalidOperationError

class SavingsAccount(BankAccount):
    def __init__(self, owner, currency, min_balance: Decimal, monthly_interest_rate: Decimal, account_id = None):
        super().__init__(owner, currency, account_id)
        
        self._validate_decimal(min_balance)
        self._validate_finite_amount(min_balance)
        self._validate_non_negative_amount(min_balance, strict=False)
        self._min_balance = min_balance

        self._validate_decimal(monthly_interest_rate)
        self._validate_finite_amount(monthly_interest_rate)
        self._validate_non_negative_amount(monthly_interest_rate, strict=False)
        self._monthly_interest_rate = monthly_interest_rate 
    
    @property
    def min_balance(self):
        return self._min_balance

    @property
    def monthly_interest_rate(self):
        return self._monthly_interest_rate

    
    def apply_monthly_interest(self) -> Decimal:
        
        self._check_status()

        interest_amount = (
            self._balance * self._monthly_interest_rate
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self._balance += interest_amount

        return self._balance

    def withdraw(self, amount):
        if self.balance - amount < self._min_balance:
            raise InvalidOperationError(
                    f"Сумма снятия превышает минимальный остаток на {self._min_balance - amount} {self.currency.value}"
                )  
        return super().withdraw(amount)
