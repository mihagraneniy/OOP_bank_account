from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class SecurityConfig:
    # --- Аутентификация ---
    max_login_attempts: int = 3

    # --- Ночные часы ---
    night_start_hour: int = 0          # 00:00
    night_end_hour: int = 5            # до 05:00 (не включительно)

    # --- Открытие счетов ---
    rapid_account_opening_threshold: int = 3
    rapid_account_opening_window_minutes: int = 5

    # --- Частота операций ---
    suspicious_frequency_threshold: int = 10
    suspicious_frequency_window_minutes: int = 10

    # --- Хранилище событий ---
    suspicious_actions_max: int = 10_000

    def is_night_time(self, now: datetime) -> bool:
        return self.night_start_hour <= now.hour < self.night_end_hour