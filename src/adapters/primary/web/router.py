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
    AddProjectRequest,
    AllTrackerProjectsResponse,
    DefaultProjectsResponse,
    ErrorResponse,
    HealthResponse,
    ProjectOperationResponse,
    RemoveProjectRequest,
    ReportRequestSchema,
    ReportStatusResponse,
    SetDefaultProjectsRequest,
    TrackerProjectInfo,
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
    "/tracker",
    response_model=AllTrackerProjectsResponse,
    summary="Все проекты из Tracker",
    description="""
Получает список ВСЕХ доступных проектов из Yandex Tracker.

Используйте этот endpoint, чтобы узнать какие проекты существуют
и затем выбрать нужные для выгрузки.
    """,
)
async def get_all_tracker_projects(
    settings: Settings = Depends(get_cached_settings),
) -> AllTrackerProjectsResponse:
    """Получает все проекты из Yandex Tracker API."""
    tracker = get_tracker_adapter(settings)
    raw_projects = tracker.get_all_projects()

    projects = [
        TrackerProjectInfo(
            id=p.get("id"),
            name=p.get("name", ""),
            description=p.get("description", ""),
        )
        for p in raw_projects
    ]

    return AllTrackerProjectsResponse(
        projects=projects,
        total=len(projects),
    )


@projects_router.get(
    "/default",
    response_model=DefaultProjectsResponse,
    summary="Проекты по умолчанию",
    description="""
Возвращает текущий список проектов по умолчанию.

Если настроен пользовательский список - вернёт его.
Иначе вернёт список из конфигурации (.env).
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
        source="env_config",
    )


@projects_router.put(
    "/default",
    response_model=ProjectOperationResponse,
    summary="Установить проекты по умолчанию",
    description="""
Устанавливает новый список проектов по умолчанию.

Этот список будет использоваться при генерации отчётов,
если не указаны конкретные проекты в запросе.

**Важно:** Полностью заменяет текущий список.
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


@projects_router.post(
    "/default/add",
    response_model=ProjectOperationResponse,
    summary="Добавить проект",
    description="Добавляет проект в список по умолчанию.",
)
async def add_default_project(
    request: AddProjectRequest,
) -> ProjectOperationResponse:
    """Добавляет проект в список по умолчанию."""
    user_settings = get_user_settings()

    if user_settings.add_project(request.project_name):
        return ProjectOperationResponse(
            success=True,
            message=f'Проект "{request.project_name}" добавлен',
            projects=user_settings.get_default_projects(),
        )

    return ProjectOperationResponse(
        success=False,
        message=f'Проект "{request.project_name}" уже в списке',
        projects=user_settings.get_default_projects(),
    )


@projects_router.post(
    "/default/remove",
    response_model=ProjectOperationResponse,
    summary="Удалить проект",
    description="Удаляет проект из списка по умолчанию.",
)
async def remove_default_project(
    request: RemoveProjectRequest,
) -> ProjectOperationResponse:
    """Удаляет проект из списка по умолчанию."""
    user_settings = get_user_settings()

    if user_settings.remove_project(request.project_name):
        return ProjectOperationResponse(
            success=True,
            message=f'Проект "{request.project_name}" удалён',
            projects=user_settings.get_default_projects(),
        )

    return ProjectOperationResponse(
        success=False,
        message=f'Проект "{request.project_name}" не найден в списке',
        projects=user_settings.get_default_projects(),
    )


@projects_router.delete(
    "/default",
    response_model=ProjectOperationResponse,
    summary="Сбросить на настройки из .env",
    description="""
Удаляет пользовательский список проектов.

После этого будет использоваться список из конфигурации (.env).
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
        message="Настройки сброшены. Используется список из .env",
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
1. Используется пользовательский список (если настроен через `/projects/default`)
2. Иначе используется список из конфигурации (.env)

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
