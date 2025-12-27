"""
Адаптер для хранения пользовательских настроек.

Сохраняет список проектов "по умолчанию" в JSON файл,
позволяя сервис-менеджерам редактировать его через API.
"""

import json
from pathlib import Path
from typing import List, Optional

from loguru import logger


class UserSettingsAdapter:
    """
    Адаптер для хранения пользовательских настроек в JSON файле.

    Позволяет сохранять и загружать список проектов по умолчанию
    без необходимости редактировать .env файл.
    """

    DEFAULT_FILENAME = "user_settings.json"

    def __init__(self, settings_path: Optional[str] = None):
        """
        Инициализирует адаптер.

        Args:
            settings_path: Путь к файлу настроек.
                          По умолчанию user_settings.json в текущей директории.
        """
        self._path = Path(settings_path or self.DEFAULT_FILENAME)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Создаёт файл настроек, если его нет."""
        if not self._path.exists():
            self._save_settings({"default_projects": []})
            logger.info(f"Создан файл настроек: {self._path}")

    def _load_settings(self) -> dict:
        """Загружает настройки из файла."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"default_projects": []}

    def _save_settings(self, settings: dict) -> None:
        """Сохраняет настройки в файл."""
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    def get_default_projects(self) -> List[str]:
        """
        Получает список проектов по умолчанию.

        Returns:
            Список названий проектов.
        """
        settings = self._load_settings()
        return settings.get("default_projects", [])

    def set_default_projects(self, projects: List[str]) -> None:
        """
        Устанавливает список проектов по умолчанию.

        Args:
            projects: Список названий проектов.
        """
        settings = self._load_settings()
        settings["default_projects"] = projects
        self._save_settings(settings)
        logger.info(f"Обновлён список проектов по умолчанию: {len(projects)} проектов")

    def add_project(self, project_name: str) -> bool:
        """
        Добавляет проект в список по умолчанию.

        Args:
            project_name: Название проекта.

        Returns:
            True если проект добавлен, False если уже существует.
        """
        projects = self.get_default_projects()
        if project_name in projects:
            return False
        projects.append(project_name)
        self.set_default_projects(projects)
        return True

    def remove_project(self, project_name: str) -> bool:
        """
        Удаляет проект из списка по умолчанию.

        Args:
            project_name: Название проекта.

        Returns:
            True если проект удалён, False если не найден.
        """
        projects = self.get_default_projects()
        if project_name not in projects:
            return False
        projects.remove(project_name)
        self.set_default_projects(projects)
        return True

    def has_default_projects(self) -> bool:
        """Проверяет, настроен ли список проектов по умолчанию."""
        return len(self.get_default_projects()) > 0
