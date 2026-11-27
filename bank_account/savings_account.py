
from decimal import Decimal, ROUND_HALF_UP

from .bank_account import BankAccount
from exceptions.exceptions import InvalidOperationError
from validators import BaseValidator


class SavingsAccount(BankAccount):

    def __init__(
        self,
        owner,
        currency,
        min_balance: Decimal,
        monthly_interest_rate: Decimal,
        account_id=None
    ) -> None:
        super().__init__(owner, currency, account_id)

        # Проверка минимального остатка
        BaseValidator.validate_amount(
            min_balance,
            "Минимальный остаток"
        )
        self._min_balance = min_balance

        # Проверка месячной процентной ставки
        BaseValidator.validate_amount(
            monthly_interest_rate,
            "Месячная процентная ставка"
        )
        self._monthly_interest_rate = monthly_interest_rate

    @property
    def min_balance(self) -> Decimal:
        return self._min_balance

    @property
    def monthly_interest_rate(self) -> Decimal:
        return self._monthly_interest_rate

    def apply_monthly_interest(self) -> Decimal:
        """Начисляет проценты на текущий баланс."""

        self._check_status()

        interest_amount = (
            self._balance * self._monthly_interest_rate
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        self._balance += interest_amount

        return self._balance

    def withdraw(self, amount: Decimal) -> None:
        """Снимает средства с учётом минимального остатка."""

        self._validate_operation(amount, strict=True)
        self._validate_withdrawal(amount)

        if self.balance - amount < self._min_balance:
            raise InvalidOperationError(
                f"После снятия баланс не может быть "
                f"меньше минимального остатка {self._min_balance}"
            )

        self._balance -= amount

    def get_account_info(self) -> dict:
        """Возвращает информацию о накопительном счёте."""

        account_info = super().get_account_info()

        account_info.update({
            "min_balance": self.min_balance,
            "monthly_interest_rate": self.monthly_interest_rate
        })

        return account_info

    def __str__(self) -> str:
        return super().__str__().replace(
            "Банковский счет:",
            "Накопительный счет:",
            1
        )
