from .bank_account import BankAccount
from .exceptions import InvalidOperationError

class PremiumAccount(BankAccount):
    def __init__(self, owner, currency, max_withdrawal, overdraft_limit, fixed_fee, account_id = None):
        super().__init__(owner, currency, account_id)
        
        self._validate_attr(max_withdrawal)
        self._max_withdrawal = max_withdrawal

        self._validate_attr(overdraft_limit)
        self._overdraft_limit = overdraft_limit

        self._validate_attr(fixed_fee)
        self._fixed_fee = fixed_fee

    @property
    def max_withdrawal(self):
        return self._max_withdrawal       

    @property
    def overdraft_limit(self):
        return self._overdraft_limit

    @property
    def fixed_fee(self):
        return self._fixed_fee



    def _check_overdraft_limit(self, amount, fee):
        new_balance = self._balance - amount - fee
        if new_balance < 0:
            if abs(new_balance) > self.overdraft_limit:
                excess = abs(new_balance) - self.overdraft_limit
                raise InvalidOperationError(
                    f"Снятие со счета {amount} превышает допустимый лимит "
                    f"{self.overdraft_limit} на {excess}"
                )
        return True

    def withdraw(self, amount):
        self._validate_operation(amount, strict=True)

        if amount > self.max_withdrawal:
            raise InvalidOperationError(
                f"Снятие со счёта {amount} превышает допустимый лимит "
                f"{self.max_withdrawal} на {amount - self.max_withdrawal}"
            )

        self._check_overdraft_limit(amount, self.fixed_fee)

        self._balance -= (amount + self.fixed_fee)


    def get_account_info(self):
        account_info = super().get_account_info()
        premium_account_info = {"max_withdrawal" : self.max_withdrawal, 
                                "overdraft_limit" : self.overdraft_limit,
                                "fixed_fee" :  self.fixed_fee}
        account_info.update(premium_account_info) 
        return account_info

    def __str__(self):
        return super().__str__().replace(
            "Банковский счет:", "Премиальный счет:", 1
        )