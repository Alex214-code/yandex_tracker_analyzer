"""
Сервис анализа статусов задач.

Содержит бизнес-логику для определения статуса на дату,
получения дат переходов и проверки активности задач.
"""

from datetime import datetime
from typing import Optional, Tuple

from src.core.domain.models import Task, TaskStatus


class StatusAnalyzerService:
    """Сервис для анализа истории статусов задач."""

    def get_status_on_date(self, task: Task, target_date: datetime) -> Optional[str]:
        """
        Определяет статус задачи на указанную дату.

        Восстанавливает статус путём обратного прохода по истории изменений.

        Args:
            task: Задача с историей изменений.
            target_date: Дата, на которую нужно определить статус.

        Returns:
            Ключ статуса на указанную дату или None, если задача ещё не существовала.
        """
        if target_date < task.created:
            return None

        if not task.changes:
            return task.status

        current_status = task.status
        sorted_changes = sorted(task.changes, key=lambda x: x.timestamp, reverse=True)

        for change in sorted_changes:
            if change.field == "status" and change.timestamp > target_date:
                current_status = change.old_value
            else:
                break

        return current_status

    def get_status_dates_in_month(
        self, task: Task, status: str, year: int, month: int
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Получает даты первого и последнего перехода в указанный статус за месяц.

        Args:
            task: Задача с историей изменений.
            status: Ключ статуса для поиска.
            year: Год периода.
            month: Месяц периода.

        Returns:
            Кортеж (первая_дата, последняя_дата). Если переходов не было - (None, None).
        """
        dates = []
        for change in task.changes:
            if (
                change.field == "status"
                and change.new_value == status
                and change.timestamp.year == year
                and change.timestamp.month == month
            ):
                dates.append(change.timestamp)

        if not dates:
            return None, None

        dates.sort()
        return dates[0], dates[-1]

    def was_in_status_during_month(
        self, task: Task, status: str, year: int, month: int, status_on_first: Optional[str]
    ) -> bool:
        """
        Проверяет, была ли задача в указанном статусе в течение месяца.

        Задача считается бывшей в статусе, если:
        - Она была в этом статусе на 1 число месяца, ИЛИ
        - Она перешла в этот статус в течение месяца

        Args:
            task: Задача для проверки.
            status: Ключ статуса.
            year: Год периода.
            month: Месяц периода.
            status_on_first: Статус задачи на 1 число месяца.

        Returns:
            True если задача была в указанном статусе.
        """
        if status_on_first == status:
            return True

        first_date, _ = self.get_status_dates_in_month(task, status, year, month)
        return first_date is not None

    def should_include_in_report(
        self, task: Task, year: int, month: int, status_on_first: Optional[str]
    ) -> bool:
        """
        Определяет, должна ли задача быть включена в отчёт за месяц.

        Задача включается если:
        - В течение месяца были изменения статуса, ИЛИ
        - На 1 число она была в незакрытом статусе, ИЛИ
        - Она была создана в этом месяце

        Args:
            task: Задача для проверки.
            year: Год периода.
            month: Месяц периода.
            status_on_first: Статус на 1 число (None если не существовала).

        Returns:
            True если задача должна быть в отчёте.
        """
        # Были изменения статуса в этом месяце
        if task.has_status_change_in_period(year, month):
            return True

        # На 1 число была в незакрытом статусе
        if status_on_first is not None and status_on_first != TaskStatus.CLOSED.value:
            return True

        # Создана в этом месяце
        if status_on_first is None and task.was_created_in_period(year, month):
            return True

        return False

    def calculate_status_flags(
        self, task: Task, year: int, month: int, status_on_first: Optional[str]
    ) -> dict:
        """
        Вычисляет флаги присутствия в статусах для задачи.

        Args:
            task: Задача для анализа.
            year: Год периода.
            month: Месяц периода.
            status_on_first: Статус на 1 число месяца.

        Returns:
            Словарь с флагами для каждого статуса.
        """
        flags = {}
        for status in TaskStatus.all_statuses():
            was_in = self.was_in_status_during_month(
                task, status.value, year, month, status_on_first
            )
            flags[status.value] = 1 if was_in else 0
        return flags

    def calculate_status_dates(self, task: Task, year: int, month: int) -> dict:
        """
        Вычисляет даты переходов в статусы для задачи.

        Args:
            task: Задача для анализа.
            year: Год периода.
            month: Месяц периода.

        Returns:
            Словарь с первой и последней датой для каждого статуса.
        """
        dates = {}
        for status in TaskStatus.all_statuses():
            first_date, last_date = self.get_status_dates_in_month(
                task, status.value, year, month
            )
            dates[f"first_{status.value}"] = first_date if first_date else "-"
            dates[f"last_{status.value}"] = last_date if last_date else "-"
        return dates
