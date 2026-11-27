
from decimal import Decimal

from .bank_account import BankAccount
from exceptions.exceptions import InvalidOperationError
from validators import BaseValidator


class PremiumAccount(BankAccount):
    def __init__(
        self,
        owner,
        currency,
        max_withdrawal: Decimal,
        overdraft_limit: Decimal,
        fixed_fee: Decimal,
        account_id=None
    ) -> None:
        super().__init__(owner, currency, account_id)

        BaseValidator.validate_amount(
            max_withdrawal, "Максимальная сумма снятия"
        )
        self._max_withdrawal = max_withdrawal

        BaseValidator.validate_amount(
            overdraft_limit, "Лимит овердрафта"
        )
        self._overdraft_limit = overdraft_limit

        BaseValidator.validate_amount(
            fixed_fee, "Фиксированная комиссия"
        )
        self._fixed_fee = fixed_fee

    @property
    def max_withdrawal(self) -> Decimal:
        return self._max_withdrawal

    @property
    def overdraft_limit(self) -> Decimal:
        return self._overdraft_limit

    @property
    def fixed_fee(self) -> Decimal:
        return self._fixed_fee

    def _check_overdraft_limit(
        self,
        amount: Decimal,
        fee: Decimal
    ) -> bool:
        new_balance = self._balance - amount - fee

        if new_balance < 0:
            if abs(new_balance) > self.overdraft_limit:
                excess = abs(new_balance) - self.overdraft_limit

                raise InvalidOperationError(
                    f"Снятие со счета {amount} превышает допустимый лимит "
                    f"{self.overdraft_limit} на {excess}"
                )

        return True

    def withdraw(self, amount: Decimal) -> None:
        self._validate_operation(amount, strict=True)

        if amount > self.max_withdrawal:
            raise InvalidOperationError(
                f"Снятие со счёта {amount} превышает допустимый лимит "
                f"{self.max_withdrawal} на "
                f"{amount - self.max_withdrawal}"
            )

        self._check_overdraft_limit(amount, self.fixed_fee)

        self._balance -= amount + self.fixed_fee

    def get_account_info(self) -> dict:
        account_info = super().get_account_info()
        account_info.update({
            "max_withdrawal": self.max_withdrawal,
            "overdraft_limit": self.overdraft_limit,
            "fixed_fee": self.fixed_fee
        })
        return account_info

    def __str__(self) -> str:
        return super().__str__().replace(
            "Банковский счет:",
            "Премиальный счет:",
            1
        )