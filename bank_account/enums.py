from enum import Enum

# Статус счета 
class AccountStatus(Enum):
    ACTIVE = "Активный"
    FROZEN = "Заморожен"
    CLOSED = "Закрыт"

# Валюта счета 
class Currency(Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    CNY = "CNY"

#Типы инвест. активов
class AssetType(Enum):
    STOCKS = "stocks"
    BONDS = "bonds"
    ETF = "etf"