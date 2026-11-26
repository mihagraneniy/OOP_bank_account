from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4
from enums.enums import ClientStatus


@dataclass
class Client:
    # Обязательные поля
    name: str
    birth_date: date
    phone: str
    email: str
    pin_code: str

    # Поля со значениями по умолчанию
    status: ClientStatus = ClientStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)
    accounts: list[UUID] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("ФИО должно быть непустой строкой")

        if not isinstance(self.birth_date, date):
            raise ValueError("Дата рождения должна иметь тип date")

        if self.birth_date > date.today():
            raise ValueError("Дата рождения не может быть в будущем")

        if not isinstance(self.phone, str) or not self.phone.strip():
            raise ValueError("Телефон должен быть непустой строкой")

        if not isinstance(self.email, str) or not self.email.strip():
            raise ValueError("Email должен быть непустой строкой")

        if not isinstance(self.status, ClientStatus):
            raise ValueError("Некорректный статус клиента")

        if not isinstance(self.id, UUID):
            raise ValueError("ID клиента должен иметь тип UUID")

        if not isinstance(self.accounts, list):
            raise ValueError("Список счетов должен иметь тип list")

        if not all(isinstance(account_id, UUID) for account_id in self.accounts):
            raise ValueError("Все ID счетов должны иметь тип UUID")

        if self.age < 18:
            raise ValueError("Возраст клиента должен быть не менее 18 лет")

        if not isinstance(self.pin_code, str):
            raise ValueError("ПИН-код должен быть строкой")

        if not (self.pin_code.isascii() and self.pin_code.isdigit()):
            raise ValueError("ПИН-код должен состоять только из цифр 0–9")

        if not (4 <= len(self.pin_code) <= 8):
            raise ValueError("ПИН-код должен содержать от 4 до 8 цифр")
         

    @property
    def age(self) -> int:
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) <
            (self.birth_date.month, self.birth_date.day)
        )
