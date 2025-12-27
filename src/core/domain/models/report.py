"""
Доменные модели отчётов.

Содержит структуры для представления строк отчёта и сводных таблиц.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class TaskReportRow:
    """
    Строка отчёта по задаче за конкретный месяц.

    Содержит все поля, которые выводятся в Excel-отчёт.
    """

    key: str
    link: str
    summary: str
    project: str
    section: str
    nesting_level: int
    assignee: str
    current_status: str
    report_period: str
    priority: str
    created_date: datetime
    updated_date: datetime
    resolved_date: Optional[datetime]
    status_on_first: str
    was_open: int
    was_in_progress: int
    was_paused: int
    was_need_info: int
    closed_in_month: int
    first_open_date: Any
    last_open_date: Any
    first_in_progress_date: Any
    last_in_progress_date: Any
    first_paused_date: Any
    last_paused_date: Any
    first_closed_date: Any
    last_closed_date: Any
    first_need_info_date: Any
    last_need_info_date: Any

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует в словарь для DataFrame."""
        return {
            "Ключ": self.key,
            "Ссылка": self.link,
            "Заголовок": self.summary,
            "Проект": self.project,
            "Раздел": self.section,
            "Уровень вложенности": self.nesting_level,
            "Исполнитель": self.assignee,
            "Текущий статус (API)": self.current_status,
            "Период отчета": self.report_period,
            "Приоритет": self.priority,
            "Дата создания": self.created_date,
            "Дата обновления": self.updated_date,
            "Дата решения": self.resolved_date,
            "Статус на 1 число": self.status_on_first,
            'Был в "Открыт"': self.was_open,
            'Был в "В работе"': self.was_in_progress,
            'Был в "Приостановлено"': self.was_paused,
            'Был в "Требуется инфо"': self.was_need_info,
            "Закрыта в этом месяце": self.closed_in_month,
            "Первый переход в Открыт": self.first_open_date,
            "Последний переход в Открыт": self.last_open_date,
            "Первый переход в В работе": self.first_in_progress_date,
            "Последний переход в В работе": self.last_in_progress_date,
            "Первый переход в Паузу": self.first_paused_date,
            "Последний переход в Паузу": self.last_paused_date,
            "Первый переход в Закрыт": self.first_closed_date,
            "Последний переход в Закрыт": self.last_closed_date,
            "Первый переход в Инфо": self.first_need_info_date,
            "Последний переход в Инфо": self.last_need_info_date,
        }


@dataclass
class WorkAnalysisRow:
    """Строка сводной таблицы 'Анализ В Работе'."""

    period: str
    project: str
    in_progress_at_start: int
    came_to_progress: int
    total_active: int
    done_from_pool: int
    remaining: int


@dataclass
class SectionSummaryRow:
    """Строка сводной таблицы по разделам."""

    period: str
    project: str
    section: str
    total_tasks: int
    was_in_progress: int
    closed_count: int


@dataclass
class StatusOnFirstRow:
    """Строка сводной таблицы 'Статусы на 1 число'."""

    period: str
    project: str
    total: int
    open_count: int
    in_progress_count: int
    paused_count: int
    closed_count: int
    need_info_count: int


@dataclass
class Report:
    """
    Полный отчёт с данными и сводными таблицами.

    Attributes:
        task_rows: Список строк с задачами.
        work_analysis: Сводная таблица анализа "В работе".
        section_summary: Сводная таблица по разделам.
        status_on_first: Сводная таблица статусов на 1 число.
    """

    task_rows: List[TaskReportRow]
    work_analysis: List[WorkAnalysisRow]
    section_summary: List[SectionSummaryRow]
    status_on_first: List[StatusOnFirstRow]
