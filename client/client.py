
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID, uuid4

from enums.enums import ClientStatus
from validators.client import ClientValidator


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

    def __post_init__(self) -> None:
        ClientValidator.validate_client_data(
            name=self.name,
            birth_date=self.birth_date,
            phone=self.phone,
            email=self.email,
            pin_code=self.pin_code,
            status=self.status,
            client_id=self.id,
            accounts=self.accounts
        )

    @property
    def age(self) -> int:
        today = date.today()

        return today.year - self.birth_date.year - (
            (today.month, today.day) <
            (self.birth_date.month, self.birth_date.day)
        )
