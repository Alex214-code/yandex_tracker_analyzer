"""
Сервис построения сводных таблиц.

Содержит бизнес-логику для формирования аналитических сводок
из списка строк отчёта.
"""

from collections import defaultdict
from typing import Dict, List

from src.core.domain.models import (
    SectionSummaryRow,
    StatusOnFirstRow,
    TaskReportRow,
    TaskStatus,
    WorkAnalysisRow,
)


class PivotBuilderService:
    """Сервис для построения сводных таблиц из данных отчёта."""

    def build_work_analysis(self, rows: List[TaskReportRow]) -> List[WorkAnalysisRow]:
        """
        Строит сводную таблицу анализа статуса "В работе".

        Показывает движение задач через статус "В работе":
        - Сколько было в работе на начало месяца
        - Сколько пришло в работу
        - Общий активный пул
        - Сколько выполнено из пула
        - Остаток в работе

        Args:
            rows: Список строк отчёта.

        Returns:
            Список строк сводной таблицы.
        """
        # Группируем по периоду и проекту
        grouped: Dict[tuple, List[TaskReportRow]] = defaultdict(list)
        for row in rows:
            grouped[(row.report_period, row.project)].append(row)

        result = []
        for (period, project), group_rows in sorted(grouped.items()):
            in_progress_display = TaskStatus.get_display_name(TaskStatus.IN_PROGRESS.value)

            start_in_work = sum(
                1 for r in group_rows if r.status_on_first == in_progress_display
            )
            arrived_in_work = sum(
                1 for r in group_rows
                if r.was_in_progress == 1 and r.status_on_first != in_progress_display
            )
            total_active = sum(r.was_in_progress for r in group_rows)
            done_from_active = sum(
                1 for r in group_rows
                if r.was_in_progress == 1 and r.closed_in_month == 1
            )

            result.append(
                WorkAnalysisRow(
                    period=period,
                    project=project,
                    in_progress_at_start=start_in_work,
                    came_to_progress=arrived_in_work,
                    total_active=total_active,
                    done_from_pool=done_from_active,
                    remaining=total_active - done_from_active,
                )
            )

        return result

    def build_section_summary(self, rows: List[TaskReportRow]) -> List[SectionSummaryRow]:
        """
        Строит сводную таблицу по разделам (контейнерам).

        Показывает статистику по каждому разделу:
        - Общее количество задач
        - Сколько было в работе
        - Сколько закрыто

        Args:
            rows: Список строк отчёта.

        Returns:
            Список строк сводной таблицы.
        """
        # Группируем по периоду, проекту и разделу
        grouped: Dict[tuple, List[TaskReportRow]] = defaultdict(list)
        for row in rows:
            grouped[(row.report_period, row.project, row.section)].append(row)

        result = []
        for (period, project, section), group_rows in sorted(grouped.items()):
            result.append(
                SectionSummaryRow(
                    period=period,
                    project=project,
                    section=section,
                    total_tasks=len(group_rows),
                    was_in_progress=sum(r.was_in_progress for r in group_rows),
                    closed_count=sum(r.closed_in_month for r in group_rows),
                )
            )

        return result

    def build_status_on_first(self, rows: List[TaskReportRow]) -> List[StatusOnFirstRow]:
        """
        Строит сводную таблицу статусов на 1 число месяца.

        Показывает распределение задач по статусам на начало каждого месяца.

        Args:
            rows: Список строк отчёта.

        Returns:
            Список строк сводной таблицы.
        """
        # Группируем по периоду и проекту
        grouped: Dict[tuple, List[TaskReportRow]] = defaultdict(list)
        for row in rows:
            grouped[(row.report_period, row.project)].append(row)

        result = []
        for (period, project), group_rows in sorted(grouped.items()):
            # Подсчитываем количество по каждому статусу
            status_counts: Dict[str, int] = defaultdict(int)
            for row in group_rows:
                status_counts[row.status_on_first] += 1

            result.append(
                StatusOnFirstRow(
                    period=period,
                    project=project,
                    total=len(group_rows),
                    open_count=status_counts.get(
                        TaskStatus.get_display_name(TaskStatus.OPEN.value), 0
                    ),
                    in_progress_count=status_counts.get(
                        TaskStatus.get_display_name(TaskStatus.IN_PROGRESS.value), 0
                    ),
                    paused_count=status_counts.get(
                        TaskStatus.get_display_name(TaskStatus.PAUSED.value), 0
                    ),
                    closed_count=status_counts.get(
                        TaskStatus.get_display_name(TaskStatus.CLOSED.value), 0
                    ),
                    need_info_count=status_counts.get(
                        TaskStatus.get_display_name(TaskStatus.NEED_INFO.value), 0
                    ),
                )
            )

        return result
