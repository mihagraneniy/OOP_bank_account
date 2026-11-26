from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from enums.enums import SuspiciousEventType


@dataclass
class SuspiciousAction:
    event_type: SuspiciousEventType
    client_id: UUID | None = None
    account_id: UUID | None = None
    details: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    id: UUID = field(default_factory=uuid4)