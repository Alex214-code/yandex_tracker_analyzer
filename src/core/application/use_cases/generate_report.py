"""
Use case генерации отчёта.

Основной сценарий использования - генерация полного отчёта
за указанный период по выбранным проектам.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from loguru import logger

from src.core.application.ports import ExportPort, TrackerPort
from src.core.domain.models import (
    Report,
    Task,
    TaskHierarchyInfo,
    TaskReportRow,
    TaskStatus,
)
from src.core.domain.services import PivotBuilderService, StatusAnalyzerService


@dataclass
class ReportRequest:
    """Запрос на генерацию отчёта."""

    start_year: int
    start_month: int
    end_year: int
    end_month: int
    projects: List[str]


@dataclass
class ReportResponse:
    """Ответ с результатом генерации отчёта."""

    success: bool
    file_bytes: Optional[bytes] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    error_message: Optional[str] = None
    tasks_count: int = 0


class GenerateReportUseCase:
    """
    Use case для генерации отчёта по задачам Yandex Tracker.

    Оркестрирует получение данных из трекера, анализ статусов,
    построение сводных таблиц и экспорт в файл.
    """

    def __init__(
        self,
        tracker_port: TrackerPort,
        export_port: ExportPort,
        status_analyzer: StatusAnalyzerService,
        pivot_builder: PivotBuilderService,
    ):
        """
        Инициализирует use case.

        Args:
            tracker_port: Порт для работы с Tracker API.
            export_port: Порт для экспорта отчёта.
            status_analyzer: Сервис анализа статусов.
            pivot_builder: Сервис построения сводных таблиц.
        """
        self._tracker = tracker_port
        self._export = export_port
        self._status_analyzer = status_analyzer
        self._pivot_builder = pivot_builder
        self._task_cache: dict = {}

    def execute(self, request: ReportRequest) -> ReportResponse:
        """
        Выполняет генерацию отчёта.

        Args:
            request: Параметры запроса.

        Returns:
            Ответ с файлом отчёта или ошибкой.
        """
        try:
            logger.info(
                f"Начинаю генерацию отчёта за период "
                f"{request.start_month:02d}.{request.start_year} - "
                f"{request.end_month:02d}.{request.end_year}"
            )

            all_rows: List[TaskReportRow] = []

            # Итерируемся по месяцам
            current_year, current_month = request.start_year, request.start_month

            while (current_year < request.end_year) or (
                current_year == request.end_year and current_month <= request.end_month
            ):
                rows = self._process_month(current_year, current_month, request.projects)
                all_rows.extend(rows)

                # Переход к следующему месяцу
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1

            if not all_rows:
                return ReportResponse(
                    success=False,
                    error_message="Нет данных за указанный период",
                )

            # Строим сводные таблицы
            logger.info("Формирую сводные таблицы...")
            report = Report(
                task_rows=all_rows,
                work_analysis=self._pivot_builder.build_work_analysis(all_rows),
                section_summary=self._pivot_builder.build_section_summary(all_rows),
                status_on_first=self._pivot_builder.build_status_on_first(all_rows),
            )

            # Экспортируем
            file_bytes = self._export.export_to_bytes(report)
            filename = (
                f"Tracker_Report_"
                f"{request.start_year}_{request.start_month:02d}-"
                f"{request.end_year}_{request.end_month:02d}"
                f"{self._export.get_file_extension()}"
            )

            logger.success(f"Отчёт сформирован: {len(all_rows)} задач")

            return ReportResponse(
                success=True,
                file_bytes=file_bytes,
                filename=filename,
                content_type=self._export.get_content_type(),
                tasks_count=len(all_rows),
            )

        except Exception as e:
            logger.error(f"Ошибка генерации отчёта: {e}")
            return ReportResponse(
                success=False,
                error_message=str(e),
            )

    def _process_month(
        self, year: int, month: int, projects: List[str]
    ) -> List[TaskReportRow]:
        """Обрабатывает задачи за один месяц."""
        first_day = datetime(year, month, 1)
        rows: List[TaskReportRow] = []

        for project_name in projects:
            logger.info(f"Обрабатываю проект '{project_name}' за {month:02d}.{year}")

            raw_tasks = self._tracker.get_tasks_by_project(project_name, year, month)
            if not raw_tasks:
                continue

            logger.info(f"Найдено {len(raw_tasks)} задач")

            # Пакетная загрузка changelog
            task_keys = [t["key"] for t in raw_tasks]
            changelogs = self._tracker.fetch_changelogs_batch(task_keys)

            for raw_task in raw_tasks:
                try:
                    task = self._tracker.parse_task(raw_task, project_name)

                    # Добавляем историю изменений
                    changelog = changelogs.get(task.key, [])
                    task.changes = self._tracker.parse_status_changes(changelog)

                    # Определяем раздел и уровень вложенности
                    hierarchy = self._resolve_hierarchy(task)

                    # Анализируем статусы
                    status_on_first = self._status_analyzer.get_status_on_date(
                        task, first_day
                    )

                    # Проверяем, нужно ли включать в отчёт
                    if not self._status_analyzer.should_include_in_report(
                        task, year, month, status_on_first
                    ):
                        continue

                    # Формируем строку отчёта
                    row = self._build_report_row(
                        task, hierarchy, year, month, status_on_first
                    )
                    rows.append(row)

                except Exception as e:
                    logger.error(f"Ошибка обработки задачи {raw_task.get('key')}: {e}")
                    continue

        return rows

    def _resolve_hierarchy(self, task: Task) -> TaskHierarchyInfo:
        """Определяет раздел и уровень вложенности задачи."""
        if not task.parent_key:
            return TaskHierarchyInfo(section_name="Контейнер", nesting_level=0)

        depth = 0
        parent_key = task.parent_key
        root_summary = "Не определен"

        while parent_key:
            depth += 1
            parent_data = self._tracker.get_task_details(parent_key)

            if not parent_data:
                break

            root_summary = parent_data.get("summary", "Без названия")

            parent_obj = parent_data.get("parent")
            if parent_obj and isinstance(parent_obj, dict) and "key" in parent_obj:
                parent_key = parent_obj["key"]
            else:
                break

        return TaskHierarchyInfo(section_name=root_summary, nesting_level=depth)

    def _build_report_row(
        self,
        task: Task,
        hierarchy: TaskHierarchyInfo,
        year: int,
        month: int,
        status_on_first: Optional[str],
    ) -> TaskReportRow:
        """Формирует строку отчёта для задачи."""
        status_flags = self._status_analyzer.calculate_status_flags(
            task, year, month, status_on_first
        )
        status_dates = self._status_analyzer.calculate_status_dates(task, year, month)

        closed_in_month = status_dates.get(f"last_{TaskStatus.CLOSED.value}") != "-"

        return TaskReportRow(
            key=task.key,
            link=f"https://tracker.yandex.ru/{task.key}",
            summary=task.summary,
            project=task.project,
            section=hierarchy.section_name,
            nesting_level=hierarchy.nesting_level,
            assignee=task.assignee,
            current_status=TaskStatus.get_display_name(task.status),
            report_period=f"{month:02d}.{year}",
            priority=task.priority,
            created_date=task.created,
            updated_date=task.updated,
            resolved_date=task.resolved,
            status_on_first=(
                TaskStatus.get_display_name(status_on_first)
                if status_on_first
                else "Не создана"
            ),
            was_open=status_flags.get(TaskStatus.OPEN.value, 0),
            was_in_progress=status_flags.get(TaskStatus.IN_PROGRESS.value, 0),
            was_paused=status_flags.get(TaskStatus.PAUSED.value, 0),
            was_need_info=status_flags.get(TaskStatus.NEED_INFO.value, 0),
            closed_in_month=1 if closed_in_month else 0,
            first_open_date=status_dates.get(f"first_{TaskStatus.OPEN.value}"),
            last_open_date=status_dates.get(f"last_{TaskStatus.OPEN.value}"),
            first_in_progress_date=status_dates.get(f"first_{TaskStatus.IN_PROGRESS.value}"),
            last_in_progress_date=status_dates.get(f"last_{TaskStatus.IN_PROGRESS.value}"),
            first_paused_date=status_dates.get(f"first_{TaskStatus.PAUSED.value}"),
            last_paused_date=status_dates.get(f"last_{TaskStatus.PAUSED.value}"),
            first_closed_date=status_dates.get(f"first_{TaskStatus.CLOSED.value}"),
            last_closed_date=status_dates.get(f"last_{TaskStatus.CLOSED.value}"),
            first_need_info_date=status_dates.get(f"first_{TaskStatus.NEED_INFO.value}"),
            last_need_info_date=status_dates.get(f"last_{TaskStatus.NEED_INFO.value}"),
        )
