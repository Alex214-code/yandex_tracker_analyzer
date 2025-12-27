"""
Зависимости FastAPI.

Определяет функции для внедрения зависимостей в обработчики запросов.
"""

from functools import lru_cache

from src.adapters.secondary.excel_export import ExcelExportAdapter
from src.adapters.secondary.tracker_api import YandexTrackerAdapter
from src.core.application.use_cases import GenerateReportUseCase
from src.core.domain.services import PivotBuilderService, StatusAnalyzerService
from src.settings import Settings, get_settings


@lru_cache
def get_cached_settings() -> Settings:
    """
    Возвращает закэшированные настройки.

    Использует lru_cache для избежания повторного чтения .env файла.
    """
    return get_settings()


def get_tracker_adapter(settings: Settings) -> YandexTrackerAdapter:
    """Создаёт адаптер Yandex Tracker."""
    return YandexTrackerAdapter(settings)


def get_export_adapter() -> ExcelExportAdapter:
    """Создаёт адаптер экспорта в Excel."""
    return ExcelExportAdapter()


def get_status_analyzer() -> StatusAnalyzerService:
    """Создаёт сервис анализа статусов."""
    return StatusAnalyzerService()


def get_pivot_builder() -> PivotBuilderService:
    """Создаёт сервис построения сводных таблиц."""
    return PivotBuilderService()


def get_generate_report_use_case(
    settings: Settings,
) -> GenerateReportUseCase:
    """
    Создаёт use case генерации отчёта.

    Собирает все необходимые зависимости.
    """
    return GenerateReportUseCase(
        tracker_port=get_tracker_adapter(settings),
        export_port=get_export_adapter(),
        status_analyzer=get_status_analyzer(),
        pivot_builder=get_pivot_builder(),
    )
