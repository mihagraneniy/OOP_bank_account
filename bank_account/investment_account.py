from .bank_account import BankAccount
from .exceptions import InvalidOperationError, InsufficientFundsError
from decimal import Decimal, ROUND_HALF_UP
from .enums import AssetType


class InvestmentAccount(BankAccount):
    
    GROWTH_RATES = {
        AssetType.STOCKS: Decimal("0.10"),
        AssetType.BONDS: Decimal("0.04"),
        AssetType.ETF: Decimal("0.07"),
    }

    ALLOWED_ASSETS = (
        AssetType.STOCKS,
        AssetType.BONDS,
        AssetType.ETF
    )

    def __init__(self, owner, currency, account_id = None):
        super().__init__(owner, currency, account_id)
        self._portfolio = {asset: Decimal("0") for asset in self.ALLOWED_ASSETS}

    @property
    def portfolio(self):
        return self._portfolio.copy()

    def _validate_asset_type(self, asset):
        if asset not in self.ALLOWED_ASSETS:
            raise InvalidOperationError(f"Указанный тип актива - {asset} не применим для данного счета.")

    def invest(self, asset_type, amount):
        self._validate_operation(amount, strict=True)
        self._validate_asset_type(asset_type)
        if amount > self._balance:            
            raise InsufficientFundsError(
                f"Недостаточно средств для инвестирования {amount}: "
                f"баланс {self._balance}, "
                f"не хватает {amount - self._balance} {self.currency.value}"
            )
        self._balance -= amount
        self._portfolio[asset_type] += amount

    def project_yearly_growth(self, growth_rates = None):
        
        if growth_rates is None: growth_rates = self.GROWTH_RATES

        for asset, rate  in growth_rates.items():
            self._validate_asset_type(asset)
            self._validate_attr(rate) 

        total = Decimal("0")

        for asset, amount in self._portfolio.items():
            rate = growth_rates.get(asset, self.GROWTH_RATES[asset])         
            total += amount * rate
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def withdraw(self, amount: Decimal):
        super().withdraw(amount)

    
    def get_account_info(self):
        """Информация об инвестиционном счёте."""
        account_info = super().get_account_info()

        account_info["portfolio"] = {
            asset.value: amount
            for asset, amount in self._portfolio.items()
        }

        return account_info


    def __str__(self):
        return super().__str__().replace(
            "Банковский счет:", "Инвестиционный счет:", 1
        )           
