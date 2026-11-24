# Исключения - BankAccountError — базовый класс
# и  четыре отдельных класса-наследника:
# AccountFrozenError, AccountClosedError, InvalidOperationError, InsufficientFundsError

class BankAccountError(Exception):
  """Базовый класс для ошибки банковского счета"""

  def __init__(self, message):
    super().__init__(message)
    self.code = self.__class__.__name__

  def __str__(self):
    return f"code: {self.code}, message: {self.args[0]}"


class AccountFrozenError(BankAccountError):
  pass

class AccountClosedError(BankAccountError):
  pass

class InvalidOperationError(BankAccountError):
  pass

class InsufficientFundsError(BankAccountError):
  pass