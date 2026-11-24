from dataclasses import dataclass
from datetime import date

@dataclass
class Client:
    name: str
    birth_date: date
    phone: str
