import heapq

from transaction.transaction import Transaction
from enums.enums import TransactionPriority


class TransactionQueue:

    PRIORITY_ORDER = {
        TransactionPriority.HIGH: 0,
        TransactionPriority.NORMAL: 1,
        TransactionPriority.LOW: 2,
    }

    def __init__(self):
        self._queue = []
        self._counter = 0
        self._transactions = {}


    def add(self, transaction: Transaction) -> None:
        if not isinstance(transaction, Transaction):
            raise TypeError("Expected Transaction instance")

        if transaction.id in self._transactions:
            raise ValueError("Transaction already exists")

        # Преобразуем приоритет в число
        priority = TransactionQueue.PRIORITY_ORDER[transaction.priority]

        # В куче меньшее значение имеет больший приоритет
        heapq.heappush(
            self._queue,
            (priority, self._counter, transaction)
        )

        self._counter += 1
        self._transactions[transaction.id] = transaction

        pass

    def get_next(self) -> Transaction | None:
        # TODO: выбрать следующую транзакцию с учётом приоритета
        # HIGH > NORMAL > LOW
        # При одинаковом приоритете раньше добавленная идёт первой
        pass

    def cancel(self, transaction_id) -> bool:
        # TODO: найти транзакцию по ID
        # TODO: отменить её, если статус допускает отмену
        # TODO: вернуть True при успехе, False если транзакция не найдена
        pass

    def schedule(self, transaction: Transaction, scheduled_at) -> None:
        # TODO: назначить время выполнения
        # TODO: перевести транзакцию в статус SCHEDULED
        pass

    def get_ready_transactions(self) -> list[Transaction]:
        # TODO: вернуть транзакции, которые уже можно обрабатывать
        # TODO: учитывать приоритет и время отложенного выполнения
        pass

    def __len__(self) -> int:
        # TODO: вернуть количество транзакций в очереди
        pass