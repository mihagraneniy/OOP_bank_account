from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4
from .enums import ClientStatus


@dataclass
class Client:
    # Обязательные поля
    name: str
    birth_date: date
    phone: str
    email: str
   
    # Поля со значениями по умолчанию
    status: ClientStatus = ClientStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)
    accounts: list[UUID] = field(default_factory=list)
    
    # Возраст через property
    @property
    def age(self) -> int:
        if not isinstance(self.birth_date, date):
            raise ValueError('Дата рождения должна иметь тип date!')    
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def __post_init__(self):
        if self.age < 18: 
            raise ValueError('Возраст должен быть от 18 лет!')