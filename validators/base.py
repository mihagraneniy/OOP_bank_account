
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from exceptions.exceptions import InvalidOperationError


class BaseValidator:
    """Базовые валидаторы для проверки типов и значений."""

    @staticmethod
    def validate_decimal(value, field_name: str = "значение") -> None:
        """Проверяет тип Decimal."""
        if not isinstance(value, Decimal):
            raise InvalidOperationError(
                f"{field_name} должно быть типом Decimal, "
                f"получен тип {type(value).__name__}"
            )

    @staticmethod
    def validate_finite(value: Decimal, field_name: str = "значение") -> None:
        """Проверяет, что Decimal является конечным числом."""
        BaseValidator.validate_decimal(value, field_name)

        if not value.is_finite():
            raise InvalidOperationError(
                f"{field_name} должно быть конечным числом, "
                f"передано {value}"
            )

    @staticmethod
    def validate_positive(value: Decimal, field_name: str = "значение") -> None:
        """Проверяет, что значение больше нуля."""
        BaseValidator.validate_finite(value, field_name)

        if value <= 0:
            raise InvalidOperationError(
                f"{field_name} должно быть больше нуля, передано {value}"
            )

    @staticmethod
    def validate_non_negative(value: Decimal, field_name: str = "значение") -> None:
        """Проверяет, что значение неотрицательное."""
        BaseValidator.validate_finite(value, field_name)

        if value < 0:
            raise InvalidOperationError(
                f"{field_name} должно быть неотрицательным, передано {value}"
            )

    @staticmethod
    def validate_amount(
        value: Decimal,
        field_name: str = "сумма",
        *,
        strict: bool = False
    ) -> None:
        """Комплексная проверка денежной суммы."""
        if strict:
            BaseValidator.validate_positive(value, field_name)
        else:
            BaseValidator.validate_non_negative(value, field_name)

    @staticmethod
    def validate_uuid(value: UUID, field_name: str = "ID") -> None:
        """Проверяет тип UUID."""
        if not isinstance(value, UUID):
            raise InvalidOperationError(
                f"{field_name} должен быть UUID, "
                f"получен тип {type(value).__name__}"
            )

    @staticmethod
    def validate_datetime(
        value: datetime,
        field_name: str = "дата",
        *,
        allow_none: bool = False
    ) -> None:
        """Проверяет тип datetime."""
        if value is None:
            if not allow_none:
                raise InvalidOperationError(
                    f"{field_name} не может быть None"
                )
            return

        if not isinstance(value, datetime):
            raise InvalidOperationError(
                f"{field_name} должен быть datetime, "
                f"получен тип {type(value).__name__}"
            )

    @staticmethod
    def validate_not_future(
        value: datetime,
        field_name: str = "дата"
    ) -> None:
        """Проверяет, что дата не находится в будущем."""
        BaseValidator.validate_datetime(value, field_name)

        if value.tzinfo is not None and value.utcoffset() is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            value = value.astimezone(timezone.utc)
        else:
            now = datetime.now()

        if value > now:
            raise InvalidOperationError(
                f"{field_name} не может быть в будущем"
            )

    @staticmethod
    def validate_type(
        value,
        expected_type: type,
        field_name: str = "значение"
    ) -> None:
        """Универсальная проверка типа."""
        if not isinstance(value, expected_type):
            raise InvalidOperationError(
                f"{field_name} должен быть {expected_type.__name__}, "
                f"получен тип {type(value).__name__}"
            )
