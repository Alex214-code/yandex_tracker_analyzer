"""
Доменная модель статусов задач.

Содержит перечисление всех возможных статусов и логику их отображения.
"""

from enum import Enum
from typing import Dict


class TaskStatus(str, Enum):
    """Перечисление статусов задач Yandex Tracker."""

    OPEN = "open"
    IN_PROGRESS = "inProgress"
    PAUSED = "paused"
    CLOSED = "closed"
    NEED_INFO = "needInfo"

    @classmethod
    def get_display_name(cls, status_key: str) -> str:
        """
        Возвращает человекочитаемое название статуса.

        Args:
            status_key: Ключ статуса из API.

        Returns:
            Отображаемое название статуса на русском языке.
        """
        mapping: Dict[str, str] = {
            cls.OPEN.value: "Открыт",
            cls.IN_PROGRESS.value: "В работе",
            cls.PAUSED.value: "Приостановлено",
            cls.CLOSED.value: "Закрыт",
            cls.NEED_INFO.value: "Требуется информация",
            # onHold из API отображается как "Приостановлено" по требованию ТЗ
            "onHold": "Приостановлено",
        }
        return mapping.get(status_key, status_key)

    @classmethod
    def all_statuses(cls) -> list["TaskStatus"]:
        """Возвращает список всех статусов для анализа."""
        return [cls.OPEN, cls.IN_PROGRESS, cls.PAUSED, cls.CLOSED, cls.NEED_INFO]

    @classmethod
    def is_active_status(cls, status_key: str) -> bool:
        """
        Проверяет, является ли статус активным (не закрытым).

        Args:
            status_key: Ключ статуса.

        Returns:
            True если задача не закрыта.
        """
        return status_key != cls.CLOSED.value
