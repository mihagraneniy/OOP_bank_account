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

# Статус клиента 
class ClientStatus(Enum):
    ACTIVE = "Активен"
    BLOCKED = "Заблокирован"
    DELETED = "Удален"

#Тип счета
class AccountType(Enum):
    DEBET = "Дебетовый"
    SAVING = "Накопительный"
    PREMIUM = "Премиум"
    INVESTMENT = "Инвестиционный"


#Подозрительные действия
class SuspiciousEventType(Enum):
    FAILED_LOGIN = "Неудачная попытка входа"
    CLIENT_BLOCKED = "Клиент заблокирован после серии неудачных входов"
    OPERATION_ON_FROZEN = "Попытка операции по замороженному счёту"
    OPERATION_ON_CLOSED = "Попытка операции по закрытому счёту"
    NIGHT_OPERATION = "Операция в ночное время"
    RAPID_ACCOUNT_OPENING = "Открытие нескольких счетов за короткое время"
    SUSPICIOUS_FREQUENCY = "Подозрительно высокая частота операций"


#Транзакции
class TransactionType(Enum):
    DEPOSIT = "пополнение"
    WITHDRAWAL = "снятие"
    INTERNAL_TRANSFER = "перевод внутри банка"
    EXTERNAL_TRANSFER = "внешний перевод"


class TransactionStatus(Enum):
    PENDING =  "ожидает обработки"
    PROCESSING = "обрабатывается"
    COMPLETED = "выполнена"
    FAILED =  "ошибка"
    CANCELLED =  "отменена"
    SCHEDULED =  "отложена"

class TransactionPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"