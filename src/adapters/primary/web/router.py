"""
FastAPI роутеры.

Определяет REST API endpoints для работы с отчётами.
"""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.adapters.primary.web.dependencies import (
    get_cached_settings,
    get_generate_report_use_case,
)
from src.adapters.primary.web.schemas import (
    ErrorResponse,
    HealthResponse,
    ProjectListResponse,
    ReportRequestSchema,
    ReportStatusResponse,
)
from src.core.application.use_cases import GenerateReportUseCase, ReportRequest
from src.settings import Settings

# Роутер для отчётов
reports_router = APIRouter(prefix="/reports", tags=["Отчёты"])

# Роутер для системных endpoints
system_router = APIRouter(tags=["Система"])


@system_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка здоровья",
    description="Проверяет доступность сервиса.",
)
async def health_check(
    settings: Settings = Depends(get_cached_settings),
) -> HealthResponse:
    """Возвращает статус здоровья сервиса."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(),
    )


@system_router.get(
    "/projects",
    response_model=ProjectListResponse,
    summary="Список проектов",
    description="Возвращает список проектов по умолчанию для выгрузки.",
)
async def get_projects(
    settings: Settings = Depends(get_cached_settings),
) -> ProjectListResponse:
    """Возвращает список доступных проектов."""
    return ProjectListResponse(projects=settings.target_projects)


@reports_router.post(
    "/generate",
    summary="Сгенерировать отчёт",
    description="""
Генерирует Excel-отчёт по задачам Yandex Tracker за указанный период.

**Параметры:**
- `start_year`, `start_month` — начало периода
- `end_year`, `end_month` — конец периода
- `projects` — список проектов (опционально, по умолчанию берутся из настроек)

**Возвращает:**
- Excel-файл (.xlsx) с несколькими листами:
  - **Все_Задачи** — полный реестр задач
  - **Анализ_В_Работе** — сводная по статусу "В работе"
  - **Сводная_по_разделам** — статистика по контейнерам
  - **Статусы_на_1_число** — распределение статусов на начало месяца

**Пример использования:**
Для отчёта за октябрь-ноябрь 2025 по всем проектам:
```json
{
  "start_year": 2025,
  "start_month": 10,
  "end_year": 2025,
  "end_month": 11
}
```
    """,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "Excel-файл с отчётом",
        },
        400: {"model": ErrorResponse, "description": "Ошибка в параметрах запроса"},
        500: {"model": ErrorResponse, "description": "Ошибка сервера"},
    },
)
async def generate_report(
    request: ReportRequestSchema,
    settings: Settings = Depends(get_cached_settings),
) -> Response:
    """
    Генерирует и возвращает Excel-отчёт.

    Этот endpoint предназначен для сервис-менеджеров,
    которые регулярно формируют отчёты для руководства.
    """
    # Валидация периода
    if (request.start_year > request.end_year) or (
        request.start_year == request.end_year
        and request.start_month > request.end_month
    ):
        raise HTTPException(
            status_code=400,
            detail="Начало периода не может быть позже конца периода",
        )

    # Определяем список проектов
    projects = request.projects or settings.target_projects

    # Создаём use case и выполняем
    use_case = get_generate_report_use_case(settings)

    report_request = ReportRequest(
        start_year=request.start_year,
        start_month=request.start_month,
        end_year=request.end_year,
        end_month=request.end_month,
        projects=projects,
    )

    result = use_case.execute(report_request)

    if not result.success:
        raise HTTPException(
            status_code=500,
            detail=result.error_message or "Ошибка генерации отчёта",
        )

    # Возвращаем файл
    return Response(
        content=result.file_bytes,
        media_type=result.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "X-Tasks-Count": str(result.tasks_count),
        },
    )


@reports_router.post(
    "/generate/status",
    response_model=ReportStatusResponse,
    summary="Проверить параметры отчёта",
    description="""
Проверяет параметры и возвращает информацию о будущем отчёте,
не генерируя сам файл. Полезно для предварительной проверки.
    """,
)
async def check_report_params(
    request: ReportRequestSchema,
    settings: Settings = Depends(get_cached_settings),
) -> ReportStatusResponse:
    """Проверяет параметры запроса без генерации отчёта."""
    # Валидация периода
    if (request.start_year > request.end_year) or (
        request.start_year == request.end_year
        and request.start_month > request.end_month
    ):
        return ReportStatusResponse(
            success=False,
            error="Начало периода не может быть позже конца периода",
        )

    projects = request.projects or settings.target_projects

    # Формируем имя файла
    filename = (
        f"Tracker_Report_"
        f"{request.start_year}_{request.start_month:02d}-"
        f"{request.end_year}_{request.end_month:02d}.xlsx"
    )

    return ReportStatusResponse(
        success=True,
        filename=filename,
        tasks_count=0,  # Неизвестно без запроса к API
    )
