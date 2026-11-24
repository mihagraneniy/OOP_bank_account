from enum import Enum

# Статус счета 
class AccountStatus(Enum):
    ACTIVE = "Активный"
    FROZEN = "Заморожен"
    CLOSED = "Закрыт"


class Currency (Enum):
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    CNY = "CNY"