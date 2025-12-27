"""
Адаптер для экспорта отчётов в Excel.

Реализует порт ExportPort для сохранения данных в формате XLSX.
"""

from io import BytesIO
from typing import Any, Dict, List

import pandas as pd
from openpyxl.utils import get_column_letter

from src.core.application.ports import ExportPort
from src.core.domain.models import Report, TaskReportRow


class ExcelExportAdapter(ExportPort):
    """
    Адаптер для экспорта отчётов в Excel (XLSX).

    Формирует файл с несколькими листами:
    - Все_Задачи: полный реестр задач
    - Анализ_В_Работе: сводная по статусу "В работе"
    - Сводная_по_разделам: статистика по контейнерам
    - Статусы_на_1_число: распределение по статусам на начало месяца
    """

    CONTENT_TYPE = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    FILE_EXTENSION = ".xlsx"

    def export_to_bytes(self, report: Report) -> bytes:
        """Экспортирует отчёт в байтовый поток."""
        output = BytesIO()

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # Лист с задачами
            tasks_df = self._build_tasks_dataframe(report.task_rows)
            tasks_df.to_excel(writer, sheet_name="Все_Задачи", index=False)

            # Сводная "Анализ В Работе"
            work_analysis_df = pd.DataFrame([
                {
                    "Период": row.period,
                    "Проект": row.project,
                    "В работе (на начало)": row.in_progress_at_start,
                    "Пришло в работу": row.came_to_progress,
                    "Всего активных (пул)": row.total_active,
                    "Выполнено из пула": row.done_from_pool,
                    "Остаток в работе": row.remaining,
                }
                for row in report.work_analysis
            ])
            work_analysis_df.to_excel(
                writer, sheet_name="Анализ_В_Работе", index=False
            )

            # Сводная по разделам
            sections_df = pd.DataFrame([
                {
                    "Период": row.period,
                    "Проект": row.project,
                    "Раздел": row.section,
                    "Всего задач": row.total_tasks,
                    "Был в работе": row.was_in_progress,
                    "Закрыто": row.closed_count,
                }
                for row in report.section_summary
            ])
            sections_df.to_excel(
                writer, sheet_name="Сводная_по_разделам", index=False
            )

            # Статусы на 1 число
            status_df = pd.DataFrame([
                {
                    "Период": row.period,
                    "Проект": row.project,
                    "Всего": row.total,
                    "Открыт": row.open_count,
                    "В работе": row.in_progress_count,
                    "Приостановлено": row.paused_count,
                    "Закрыт": row.closed_count,
                    "Требуется информация": row.need_info_count,
                }
                for row in report.status_on_first
            ])
            status_df.to_excel(
                writer, sheet_name="Статусы_на_1_число", index=False
            )

            # Автоподбор ширины колонок
            self._autofit_columns(writer)

        output.seek(0)
        return output.getvalue()

    def export_to_file(self, report: Report, filepath: str) -> None:
        """Экспортирует отчёт в файл."""
        data = self.export_to_bytes(report)
        with open(filepath, "wb") as f:
            f.write(data)

    def get_content_type(self) -> str:
        """Возвращает MIME-тип для Excel."""
        return self.CONTENT_TYPE

    def get_file_extension(self) -> str:
        """Возвращает расширение файла."""
        return self.FILE_EXTENSION

    def _build_tasks_dataframe(self, rows: List[TaskReportRow]) -> pd.DataFrame:
        """Формирует DataFrame из строк отчёта."""
        data = [row.to_dict() for row in rows]
        return pd.DataFrame(data)

    def _autofit_columns(self, writer: pd.ExcelWriter) -> None:
        """Автоматически подбирает ширину колонок во всех листах."""
        for sheet in writer.sheets.values():
            for column in sheet.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)

                for cell in column:
                    try:
                        cell_length = len(str(cell.value))
                        if cell_length > max_length:
                            max_length = cell_length
                    except (TypeError, AttributeError):
                        pass

                # Ограничиваем максимальную ширину
                adjusted_width = min(max_length + 2, 60)
                sheet.column_dimensions[column_letter].width = adjusted_width
