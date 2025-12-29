"""
FastAPI роутеры.

Определяет REST API endpoints для работы с отчётами и проектами.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.adapters.primary.web.dependencies import (
    get_cached_settings,
    get_generate_report_use_case,
    get_tracker_adapter,
    get_user_settings,
)
from src.adapters.primary.web.schemas import (
    DefaultProjectsResponse,
    ErrorResponse,
    HealthResponse,
    ProjectFilterValuesResponse,
    ProjectOperationResponse,
    ReportRequestSchema,
    ReportStatusResponse,
    SetDefaultProjectsRequest,
)
from src.core.application.use_cases import ReportRequest
from src.settings import Settings

# Роутер для отчётов
reports_router = APIRouter(prefix="/reports", tags=["Отчёты"])

# Роутер для управления проектами
projects_router = APIRouter(prefix="/projects", tags=["Проекты"])

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


# --- Endpoints для управления проектами ---


@projects_router.get(
    "/available",
    response_model=ProjectFilterValuesResponse,
    summary="Получить все доступные проекты",
    description="""
Возвращает список всех проектов, которые существуют в Yandex Tracker.

Используйте этот endpoint, чтобы узнать какие проекты доступны
для выгрузки отчётов. Полученные названия можно:

- Сохранить как список по умолчанию через `PUT /projects/default`
- Передать напрямую в запрос `POST /reports/generate`
    """,
)
async def get_available_projects(
    settings: Settings = Depends(get_cached_settings),
) -> ProjectFilterValuesResponse:
    """Получает список всех доступных проектов."""
    tracker = get_tracker_adapter(settings)
    values = tracker.get_unique_project_values()

    return ProjectFilterValuesResponse(
        values=values,
        total=len(values),
    )


@projects_router.get(
    "/default",
    response_model=DefaultProjectsResponse,
    summary="Посмотреть список проектов по умолчанию",
    description="""
Показывает, какие проекты используются для генерации отчётов по умолчанию.

Если список не был изменён через `PUT /projects/default`, возвращаются
встроенные значения из кода.

В ответе указан источник настроек:
- `user_settings` — список был изменён через `PUT /projects/default`
- `builtin` — используются встроенные значения из кода
    """,
)
async def get_default_projects(
    settings: Settings = Depends(get_cached_settings),
) -> DefaultProjectsResponse:
    """Получает список проектов по умолчанию."""
    user_settings = get_user_settings()

    if user_settings.has_default_projects():
        return DefaultProjectsResponse(
            projects=user_settings.get_default_projects(),
            source="user_settings",
        )

    return DefaultProjectsResponse(
        projects=settings.target_projects,
        source="builtin",
    )


@projects_router.put(
    "/default",
    response_model=ProjectOperationResponse,
    summary="Изменить список проектов по умолчанию",
    description="""
Сохраняет новый список проектов, который будет использоваться при генерации отчётов.

После сохранения не нужно каждый раз указывать проекты в запросе —
достаточно задать только период, и отчёт сформируется по сохранённому списку.

Чтобы узнать какие проекты доступны, сначала вызовите `GET /projects/available`.
    """,
)
async def set_default_projects(
    request: SetDefaultProjectsRequest,
) -> ProjectOperationResponse:
    """Устанавливает список проектов по умолчанию."""
    user_settings = get_user_settings()
    user_settings.set_default_projects(request.projects)

    return ProjectOperationResponse(
        success=True,
        message=f"Установлено {len(request.projects)} проектов по умолчанию",
        projects=request.projects,
    )


@projects_router.delete(
    "/default",
    response_model=ProjectOperationResponse,
    summary="Сбросить к встроенным значениям из кода",
    description="""
Удаляет сохранённый список проектов и возвращает встроенные значения из кода.

Встроенные проекты заданы в коде приложения.
    """,
)
async def reset_default_projects(
    settings: Settings = Depends(get_cached_settings),
) -> ProjectOperationResponse:
    """Сбрасывает пользовательские настройки проектов."""
    user_settings = get_user_settings()
    user_settings.set_default_projects([])

    return ProjectOperationResponse(
        success=True,
        message="Настройки сброшены. Используются встроенные значения из кода",
        projects=settings.target_projects,
    )


# --- Endpoints для отчётов ---


@reports_router.post(
    "/generate",
    summary="Сгенерировать отчёт",
    description="""
Генерирует Excel-отчёт по задачам Yandex Tracker за указанный период.

**Параметры:**
- `start_year`, `start_month` — начало периода
- `end_year`, `end_month` — конец периода
- `projects` — список проектов (опционально)

**Если projects не указан:**
1. Используется пользовательский список (если настроен через `PUT /projects/default`)
2. Иначе используются встроенные значения из кода

**Возвращает Excel-файл с листами:**
- **Все_Задачи** — полный реестр задач
- **Анализ_В_Работе** — сводная по статусу "В работе"
- **Сводная_по_разделам** — статистика по контейнерам
- **Статусы_на_1_число** — распределение статусов на начало месяца
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
    if request.projects:
        projects = request.projects
    else:
        # Проверяем пользовательские настройки
        user_settings = get_user_settings()
        if user_settings.has_default_projects():
            projects = user_settings.get_default_projects()
        else:
            projects = settings.target_projects

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

    # Определяем проекты
    if request.projects:
        projects = request.projects
    else:
        user_settings = get_user_settings()
        if user_settings.has_default_projects():
            projects = user_settings.get_default_projects()
        else:
            projects = settings.target_projects

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
