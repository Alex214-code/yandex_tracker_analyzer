"""
Порт для работы с Yandex Tracker API.

Определяет интерфейс, который должен реализовать адаптер
для взаимодействия с внешним API трекера.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.core.domain.models import Task, TaskChange


class TrackerPort(ABC):
    """
    Абстрактный порт для работы с Yandex Tracker API.

    Адаптер должен реализовать этот интерфейс для обеспечения
    доступа к данным трекера.
    """

    @abstractmethod
    def get_tasks_by_project(
        self, project_name: str, year: int, month: int
    ) -> List[Dict]:
        """
        Получает список задач проекта за указанный месяц.

        Args:
            project_name: Название проекта.
            year: Год периода.
            month: Месяц периода.

        Returns:
            Список сырых данных задач из API.
        """
        pass

    @abstractmethod
    def get_task_changelog(self, task_key: str) -> List[Dict]:
        """
        Получает историю изменений задачи.

        Args:
            task_key: Ключ задачи (например, PROJ-123).

        Returns:
            Список записей changelog из API.
        """
        pass

    @abstractmethod
    def get_task_details(self, task_key: str) -> Optional[Dict]:
        """
        Получает детальную информацию о задаче.

        Args:
            task_key: Ключ задачи.

        Returns:
            Данные задачи или None если не найдена.
        """
        pass

    @abstractmethod
    def fetch_changelogs_batch(self, task_keys: List[str]) -> Dict[str, List[Dict]]:
        """
        Пакетно загружает changelog для списка задач.

        Args:
            task_keys: Список ключей задач.

        Returns:
            Словарь {task_key: changelog_data}.
        """
        pass

    @abstractmethod
    def parse_task(self, raw_data: Dict, project_name: str) -> Task:
        """
        Преобразует сырые данные API в доменную модель Task.

        Args:
            raw_data: Данные задачи из API.
            project_name: Название проекта.

        Returns:
            Объект Task.
        """
        pass

    @abstractmethod
    def parse_status_changes(self, changelog: List[Dict]) -> List[TaskChange]:
        """
        Извлекает изменения статуса из changelog.

        Args:
            changelog: Данные changelog из API.

        Returns:
            Список изменений статуса.
        """
        pass

    @abstractmethod
    def get_all_projects(self) -> List[Dict]:
        """
        Получает список всех доступных проектов из Yandex Tracker.

        Returns:
            Список проектов с полями id, name, description.
        """
        pass
