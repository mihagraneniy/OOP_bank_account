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

        return self._queue[0][2]


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