
from datetime import date
from uuid import UUID

from enums.enums import ClientStatus


class ClientValidator:
    """Валидаторы для данных клиента."""

    @staticmethod
    def validate_name(name: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("ФИО должно быть непустой строкой")

    @staticmethod
    def validate_birth_date(birth_date: date) -> None:
        if not isinstance(birth_date, date):
            raise ValueError("Дата рождения должна иметь тип date")

        if birth_date > date.today():
            raise ValueError("Дата рождения не может быть в будущем")

    @staticmethod
    def validate_age(birth_date: date) -> None:
        today = date.today()

        age = today.year - birth_date.year - (
            (today.month, today.day) <
            (birth_date.month, birth_date.day)
        )

        if age < 18:
            raise ValueError(
                "Возраст клиента должен быть не менее 18 лет"
            )

    @staticmethod
    def validate_phone(phone: str) -> None:
        if not isinstance(phone, str) or not phone.strip():
            raise ValueError("Телефон должен быть непустой строкой")

    @staticmethod
    def validate_email(email: str) -> None:
        if not isinstance(email, str) or not email.strip():
            raise ValueError("Email должен быть непустой строкой")

    @staticmethod
    def validate_status(status: ClientStatus) -> None:
        if not isinstance(status, ClientStatus):
            raise ValueError("Некорректный статус клиента")

    @staticmethod
    def validate_id(client_id: UUID) -> None:
        if not isinstance(client_id, UUID):
            raise ValueError("ID клиента должен иметь тип UUID")

    @staticmethod
    def validate_accounts(accounts: list) -> None:
        if not isinstance(accounts, list):
            raise ValueError("Список счетов должен иметь тип list")

        if not all(
            isinstance(account_id, UUID)
            for account_id in accounts
        ):
            raise ValueError("Все ID счетов должны иметь тип UUID")

    @staticmethod
    def validate_pin_code(pin_code: str) -> None:
        if not isinstance(pin_code, str):
            raise ValueError("ПИН-код должен быть строкой")

        if not (pin_code.isascii() and pin_code.isdigit()):
            raise ValueError(
                "ПИН-код должен состоять только из цифр 0–9"
            )

        if not (4 <= len(pin_code) <= 8):
            raise ValueError(
                "ПИН-код должен содержать от 4 до 8 цифр"
            )

    @classmethod
    def validate_client_data(
        cls,
        name: str,
        birth_date: date,
        phone: str,
        email: str,
        pin_code: str,
        status: ClientStatus,
        client_id: UUID,
        accounts: list
    ) -> None:
        """Комплексная проверка данных клиента."""

        cls.validate_name(name)
        cls.validate_birth_date(birth_date)
        cls.validate_phone(phone)
        cls.validate_email(email)
        cls.validate_status(status)
        cls.validate_id(client_id)
        cls.validate_accounts(accounts)
        cls.validate_age(birth_date)
        cls.validate_pin_code(pin_code)