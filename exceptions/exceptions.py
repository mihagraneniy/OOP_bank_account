# Исключения - BaseError — базовый класс

class BaseError(Exception):
  """Базовый класс для ошибки банковского счета"""

  def __init__(self, message):
    super().__init__(message)
    self.code = self.__class__.__name__

  def __str__(self):
    return f"code: {self.code}, message: {self.args[0]}"

#  BankAccountError - класс ошибки для счета
# и  четыре отдельных класса-наследника:
# AccountFrozenError, AccountClosedError, InvalidOperationError, InsufficientFundsError

class BankAccountError(BaseError):
  pass

class AccountFrozenError(BankAccountError):
  pass

class AccountClosedError(BankAccountError):
  pass

class InvalidOperationError(BankAccountError):
  pass

class InsufficientFundsError(BankAccountError):
  pass

class AccountNotFoundError(BankAccountError):
    pass

# Исключения - BankError — базовый класс
class BankError(BaseError):
    """Базовое исключение для операций банка."""
    pass

class ClientNotFoundError(BankError):
    pass

class AuthenticationError(BankError):
    pass

class ClientBlockedError(BankError):
    pass


class SuspiciousActivityError(BankError):
    pass


class OperationTimeError(BankError):
    pass


#Транзакции
class TransactionStatusError(BankError):
    pass