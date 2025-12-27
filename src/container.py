"""
DI Container - сборка зависимостей приложения.

Отвечает за создание и связывание всех компонентов системы.
"""

from dataclasses import dataclass

from src.adapters.secondary.excel_export import ExcelExportAdapter
from src.adapters.secondary.tracker_api import YandexTrackerAdapter
from src.core.application.ports import ExportPort, TrackerPort
from src.core.application.use_cases import GenerateReportUseCase
from src.core.domain.services import PivotBuilderService, StatusAnalyzerService
from src.settings import Settings


@dataclass
class Container:
    """
    Контейнер зависимостей приложения.

    Хранит все сервисы и адаптеры, обеспечивая их правильную инициализацию.
    """

    settings: Settings
    tracker_adapter: TrackerPort
    export_adapter: ExportPort
    status_analyzer: StatusAnalyzerService
    pivot_builder: PivotBuilderService
    generate_report_use_case: GenerateReportUseCase


def create_container(settings: Settings) -> Container:
    """
    Создаёт контейнер с инициализированными зависимостями.

    Args:
        settings: Настройки приложения.

    Returns:
        Контейнер с готовыми к использованию сервисами.
    """
    # Создаём адаптеры
    tracker_adapter = YandexTrackerAdapter(settings)
    export_adapter = ExcelExportAdapter()

    # Создаём доменные сервисы
    status_analyzer = StatusAnalyzerService()
    pivot_builder = PivotBuilderService()

    # Создаём use cases
    generate_report_use_case = GenerateReportUseCase(
        tracker_port=tracker_adapter,
        export_port=export_adapter,
        status_analyzer=status_analyzer,
        pivot_builder=pivot_builder,
    )

    return Container(
        settings=settings,
        tracker_adapter=tracker_adapter,
        export_adapter=export_adapter,
        status_analyzer=status_analyzer,
        pivot_builder=pivot_builder,
        generate_report_use_case=generate_report_use_case,
    )
