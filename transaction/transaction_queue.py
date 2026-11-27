import heapq

from transaction.transaction import Transaction
from enums.enums import TransactionPriority, TransactionStatus
from validators import TransactionValidator

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
        TransactionValidator.validate_types(transaction=transaction)

        if transaction.id in self._transactions:
            raise ValueError(
                f"Транзакция {transaction.id} уже находится в очереди!"
            )

        priority = self.PRIORITY_ORDER[transaction.priority]

        heapq.heappush(
            self._queue,
            (priority, self._counter, transaction)
        )

        self._counter += 1
        self._transactions[transaction.id] = transaction

    def get_next(self) -> Transaction | None:
        if not self._queue:
            return None

        item = min(
            (
                entry for entry in self._queue
                if entry[2].status != TransactionStatus.CANCELLED
            ),
            key=lambda entry: (entry[0], entry[1]),
            default=None,
        )
        return item[2] if item is not None else None

    def cancel(self, transaction_id) -> bool:
        transaction = self._transactions.get(transaction_id)

        if transaction is None:
            return False

        transaction.cancel()

        return True

    def pop_next(self) -> Transaction | None:

        while self._queue:
            transaction = heapq.heappop(self._queue)[2]
            
            self._transactions.pop(transaction.id, None)

            if transaction.status == TransactionStatus.CANCELLED:
                continue
        
            return transaction
        
        return None

    def __len__(self)-> int:
        return len(self._queue)