from decimal import Decimal, ROUND_HALF_UP
from .bank_account import BankAccount
from .exceptions import InvalidOperationError, InsufficientFundsError

class SavingsAccount(BankAccount):
    
    def __init__(self, owner, currency, min_balance: Decimal, monthly_interest_rate: Decimal, account_id = None):
        super().__init__(owner, currency, account_id)
        
        self._validate_attr(min_balance)
        self._min_balance = min_balance

        self._validate_attr(monthly_interest_rate)
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

    def withdraw(self, amount: Decimal):
        self._validate_operation(amount, strict = True)
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
        return super().__str__().replace(
            "Банковский счет:", "Накопительный счет:", 1
        )