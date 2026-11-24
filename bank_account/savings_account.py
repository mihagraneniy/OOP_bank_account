from decimal import Decimal, ROUND_HALF_UP
from .bank_account import BankAccount
from .exceptions import InvalidOperationError, InsufficientFundsError

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

    def _validate_withdrawal(self, amount: Decimal):
        self._validate_operation(amount, strict=True)

        if amount > self.balance:
            raise InsufficientFundsError(
                f"Сумма списания {amount} превышает "
                f"текущий баланс {self.balance} "
                f"на {amount - self.balance} {self.currency.value}"
            )
    
    def apply_monthly_interest(self) -> Decimal:
        
        self._check_status()

        interest_amount = (
            self._balance * self._monthly_interest_rate
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        self._balance += interest_amount

        return self._balance

    def withdraw(self, amount: Decimal):
        self._validate_withdrawal(amount)

        if self.balance - amount < self._min_balance:
            raise InvalidOperationError(
                f"После снятия баланс не может быть "
                f"меньше минимального остатка {self._min_balance}"
            )

        self._balance -= amount

    def get_account_info(self):
        account_info = super().get_account_info()
        savings_account_info = {'min_balance': self.min_balance, 'monthly_interest_rate':self.monthly_interest_rate}
        account_info.update(savings_account_info)      
        return account_info
    
    def __str__(self):
        pairs = ", \n".join(f"{k}:{v}" for k, v in self.get_account_info().items())
        return f"Накопительный счёт: ({pairs})" 