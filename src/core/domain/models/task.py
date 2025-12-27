"""
Доменные модели задач Yandex Tracker.

Содержит основные сущности: Task, TaskChange.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class TaskChange:
    """
    Изменение статуса задачи.

    Attributes:
        timestamp: Время изменения.
        field: Название измененного поля.
        old_value: Предыдущее значение.
        new_value: Новое значение.
    """

    timestamp: datetime
    field: str
    old_value: str
    new_value: str


@dataclass
class Task:
    """
    Доменная модель задачи Yandex Tracker.

    Attributes:
        key: Уникальный ключ задачи (например, PROJ-123).
        summary: Заголовок задачи.
        project: Название проекта.
        assignee: Имя исполнителя.
        status: Текущий статус задачи.
        created: Дата создания.
        updated: Дата последнего обновления.
        resolved: Дата закрытия (если есть).
        parent_key: Ключ родительской задачи.
        priority: Приоритет задачи.
        changes: История изменений статуса.
    """

    key: str
    summary: str
    project: str
    assignee: str
    status: str
    created: datetime
    updated: datetime
    resolved: Optional[datetime] = None
    parent_key: Optional[str] = None
    priority: str = ""
    changes: List[TaskChange] = field(default_factory=list)

    def has_status_change_in_period(self, year: int, month: int) -> bool:
        """Проверяет, были ли изменения статуса в указанном периоде."""
        return any(
            c.timestamp.year == year and c.timestamp.month == month
            for c in self.changes
            if c.field == "status"
        )

    def was_created_in_period(self, year: int, month: int) -> bool:
        """Проверяет, была ли задача создана в указанном периоде."""
        return self.created.year == year and self.created.month == month


@dataclass
class TaskHierarchyInfo:
    """
    Информация об иерархии задачи.

    Attributes:
        section_name: Название корневого раздела (контейнера).
        nesting_level: Уровень вложенности задачи.
    """

    section_name: str
    nesting_level: int
