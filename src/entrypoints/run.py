"""
Точка входа приложения.

Запускает FastAPI сервер с Swagger UI для генерации отчётов.
"""

import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from loguru import logger

from src.adapters.primary.web import projects_router, reports_router, system_router
from src.adapters.secondary.user_settings import UserSettingsAdapter
from src.settings import get_settings


def configure_logging(settings) -> None:
    """Настраивает логирование приложения."""
    logger.remove()

    # Формат логов
    if settings.log_format == "json":
        log_format = (
            '{{"time":"{time:YYYY-MM-DDTHH:mm:ss.SSS}", '
            '"level":"{level}", '
            '"pid":{process}, '
            '"message":"{message}"}}'
        )
    else:
        log_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | "
            "PID:{process} | {message}"
        )

    # Вывод в stdout (для Docker)
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=settings.log_format != "json",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управление жизненным циклом приложения.

    Выполняет инициализацию при старте и очистку при завершении.
    """
    settings = get_settings()
    configure_logging(settings)

    logger.info(f"Запуск {settings.app_name} v{settings.app_version}")
    logger.info(f"Режим отладки: {settings.debug}")

    # Проверяем пользовательские настройки
    user_settings = UserSettingsAdapter()
    user_projects = user_settings.get_default_projects()
    if user_projects:
        logger.info("При генерации отчёта будут использованы проекты из user_settings.json")
        logger.info(f"Проекты из user_settings.json: {user_projects}")
    else:
        logger.info("Пользовательские настройки не заданы, используются проекты по умолчанию из кода")
        logger.info(f"Проекты по умолчанию из кода: {settings.target_projects}")

    yield

    logger.info("Завершение работы приложения")


def create_app() -> FastAPI:
    """
    Создаёт и настраивает FastAPI приложение.

    Returns:
        Настроенное FastAPI приложение.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="""
## Yandex Tracker Analyzer API

Сервис для генерации Excel-отчётов по задачам Yandex Tracker.

**Предназначен для сервис-менеджеров**, которым нужно регулярно формировать
отчёты для руководства без привлечения программистов.

### Быстрый старт:
1. **Посмотрите проекты**: `/projects/available` — все доступные проекты
2. **Настройте список**: `/projects/default` — установить проекты по умолчанию
3. **Генерируйте отчёт**: `/reports/generate` — получить Excel-файл

### Возможности:
- **Динамический список проектов** — загружается из Yandex Tracker
- **Настраиваемый список по умолчанию** — сохраняется между сессиями
- **Помесячная разбивка** — одна строка = одна задача в одном месяце
- **Учет статусов** — статус на начало месяца и переходы внутри месяца
- **Активный пул** — логика "был в работе на начало или перешел в работу"
- **Иерархия задач** — разделы определяются по корневой родительской задаче

### Формат отчёта:
Excel-файл с листами:
- **Все_Задачи** — полный реестр задач
- **Анализ_В_Работе** — сводная по статусу "В работе"
- **Сводная_по_разделам** — статистика по контейнерам
- **Статусы_на_1_число** — распределение статусов на начало месяца
        """,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Подключаем роутеры
    app.include_router(system_router)
    app.include_router(projects_router)
    app.include_router(reports_router)

    return app


# Создаём приложение для uvicorn
app = create_app()


def main() -> None:
    """Запускает сервер uvicorn."""
    settings = get_settings()

    uvicorn.run(
        "src.entrypoints.run:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
