"""
Настройки приложения.

Все настройки загружаются из переменных окружения с возможностью
указания значений по умолчанию.
"""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфигурация приложения Yandex Tracker Analyzer."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Yandex Tracker API
    yandex_client_id: str = Field(
        ...,
        description="Client ID приложения Yandex OAuth",
    )
    yandex_oauth_token: str = Field(
        ...,
        description="OAuth токен для доступа к Yandex Tracker API",
    )
    yandex_org_id: str = Field(
        ...,
        description="ID организации в Yandex Tracker",
    )

    # API Settings
    tracker_api_base_url: str = Field(
        default="https://api.tracker.yandex.net/v2",
        description="Базовый URL Yandex Tracker API",
    )
    api_timeout: int = Field(
        default=30,
        description="Таймаут запросов к API в секундах",
    )
    api_max_retries: int = Field(
        default=3,
        description="Максимальное количество повторных попыток запроса",
    )
    api_max_workers: int = Field(
        default=5,
        description="Количество потоков для параллельных запросов",
    )

    # Target Projects
    target_projects: List[str] = Field(
        default=[
            "НорНикель НОФ (Тех. Поддержка)",
            "УГМК Святогор (Тех. Поддержка)",
            "УГМК Гайский ГОК (Тех. Поддержка)",
            "РМК Томинский ГОК (Тех. Поддержка)",
        ],
        description="Список проектов для выгрузки",
    )

    # Application Settings
    app_name: str = Field(
        default="Yandex Tracker Analyzer",
        description="Название приложения",
    )
    app_version: str = Field(
        default="1.0.0",
        description="Версия приложения",
    )
    debug: bool = Field(
        default=False,
        description="Режим отладки",
    )

    # Server Settings
    host: str = Field(
        default="0.0.0.0",
        description="Хост для запуска сервера",
    )
    port: int = Field(
        default=8000,
        description="Порт для запуска сервера",
    )
    workers: int = Field(
        default=1,
        description="Количество воркеров uvicorn",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Уровень логирования (DEBUG, INFO, WARNING, ERROR)",
    )
    log_format: str = Field(
        default="json",
        description="Формат логов (json, text)",
    )


def get_settings() -> Settings:
    """Возвращает экземпляр настроек приложения."""
    return Settings()
