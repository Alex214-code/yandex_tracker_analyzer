"""
Pydantic схемы для Web API.

Определяет модели запросов и ответов для REST API.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ReportRequestSchema(BaseModel):
    """
    Схема запроса на генерацию отчёта.

    Используется в Swagger UI для ввода параметров.
    """

    start_year: int = Field(
        ...,
        ge=2020,
        le=2030,
        description="Год начала периода",
        examples=[2025],
    )
    start_month: int = Field(
        ...,
        ge=1,
        le=12,
        description="Месяц начала периода (1-12)",
        examples=[10],
    )
    end_year: int = Field(
        ...,
        ge=2020,
        le=2030,
        description="Год окончания периода",
        examples=[2025],
    )
    end_month: int = Field(
        ...,
        ge=1,
        le=12,
        description="Месяц окончания периода (1-12)",
        examples=[11],
    )
    projects: Optional[List[str]] = Field(
        default=None,
        description=(
            "Список проектов для выгрузки. "
            "Если не указан, используются проекты по умолчанию из настроек."
        ),
        examples=[
            [
                "НорНикель НОФ (Тех. Поддержка)",
                "УГМК Святогор (Тех. Поддержка)",
            ]
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "start_year": 2025,
                    "start_month": 10,
                    "end_year": 2025,
                    "end_month": 11,
                    "projects": None,
                }
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Схема ответа с ошибкой."""

    success: bool = False
    error: str = Field(..., description="Описание ошибки")


class HealthResponse(BaseModel):
    """Схема ответа проверки здоровья."""

    status: str = Field(..., description="Статус сервиса")
    version: str = Field(..., description="Версия приложения")
    timestamp: datetime = Field(..., description="Время ответа")


class ProjectListResponse(BaseModel):
    """Схема ответа со списком проектов."""

    projects: List[str] = Field(..., description="Список доступных проектов")


class ReportStatusResponse(BaseModel):
    """Схема ответа о статусе генерации отчёта."""

    success: bool = Field(..., description="Успешность генерации")
    tasks_count: int = Field(0, description="Количество задач в отчёте")
    filename: Optional[str] = Field(None, description="Имя файла отчёта")
    error: Optional[str] = Field(None, description="Сообщение об ошибке")
