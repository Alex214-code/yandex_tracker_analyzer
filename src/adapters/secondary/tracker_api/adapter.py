"""
Адаптер для работы с Yandex Tracker API.

Реализует порт TrackerPort для взаимодействия с внешним API.
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from loguru import logger

from src.core.application.ports import TrackerPort
from src.core.domain.models import Task, TaskChange
from src.settings import Settings


class YandexTrackerAdapter(TrackerPort):
    """
    Адаптер для Yandex Tracker API.

    Реализует все методы порта TrackerPort, обеспечивая
    доступ к данным задач и их истории изменений.
    """

    def __init__(self, settings: Settings):
        """
        Инициализирует адаптер.

        Args:
            settings: Настройки приложения с credentials.
        """
        self._settings = settings
        self._base_url = settings.tracker_api_base_url
        self._timeout = settings.api_timeout
        self._max_retries = settings.api_max_retries
        self._max_workers = settings.api_max_workers

        self._headers = {
            "Authorization": f"OAuth {settings.yandex_oauth_token}",
            "X-Org-ID": settings.yandex_org_id,
            "Content-Type": "application/json",
        }

        self._client = httpx.Client(
            headers=self._headers,
            timeout=self._timeout,
        )

        # Кэши
        self._changelog_cache: Dict[str, List[Dict]] = {}
        self._task_cache: Dict[str, Dict] = {}

    def __del__(self):
        """Закрывает HTTP клиент при удалении объекта."""
        if hasattr(self, "_client"):
            self._client.close()

    def get_tasks_by_project(
        self, project_name: str, year: int, month: int
    ) -> List[Dict]:
        """Получает список задач проекта за указанный месяц."""
        tasks: List[Dict] = []
        page = 1

        # Вычисляем границы месяца
        first_day = datetime(year, month, 1)
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)

        date_from = first_day.strftime("%Y-%m-%d")
        date_to = next_month.strftime("%Y-%m-%d")

        logger.info(f"Запрашиваю задачи проекта '{project_name}' за {month:02d}.{year}")

        # Формируем запрос
        filter_query = (
            f'Project: "{project_name}" AND ('
            f'(Updated: >= "{date_from}" AND Updated: < "{date_to}") OR '
            f'(Created: < "{date_to}" AND (Resolved: empty() OR Resolved: >= "{date_from}"))'
            f")"
        )

        while True:
            try:
                response = self._client.post(
                    f"{self._base_url}/issues/_search",
                    params={"perPage": 100, "page": page},
                    json={"query": filter_query},
                )

                if response.status_code == 429:
                    logger.warning("Rate limit, ожидаю 5 сек...")
                    time.sleep(5)
                    continue

                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                tasks.extend(data)
                page += 1

            except httpx.HTTPError as e:
                logger.error(f"Ошибка при получении задач: {e}")
                break

        return tasks

    def get_task_changelog(self, task_key: str) -> List[Dict]:
        """Получает историю изменений задачи."""
        if task_key in self._changelog_cache:
            return self._changelog_cache[task_key]

        try:
            response = self._client.get(
                f"{self._base_url}/issues/{task_key}/changelog"
            )
            response.raise_for_status()
            changelog = response.json()
            self._changelog_cache[task_key] = changelog
            return changelog
        except httpx.HTTPError:
            return []

    def get_task_details(self, task_key: str) -> Optional[Dict]:
        """Получает детальную информацию о задаче."""
        if task_key in self._task_cache:
            return self._task_cache[task_key]

        try:
            response = self._client.get(
                f"{self._base_url}/issues/{task_key}",
                params={"fields": "summary,parent"},
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            data = response.json()
            self._task_cache[task_key] = data
            return data

        except httpx.HTTPError as e:
            logger.warning(f"Не удалось получить информацию о задаче {task_key}: {e}")
            return None

    def fetch_changelogs_batch(self, task_keys: List[str]) -> Dict[str, List[Dict]]:
        """Пакетно загружает changelog для списка задач."""
        # Фильтруем уже загруженные
        keys_to_fetch = [k for k in task_keys if k not in self._changelog_cache]

        if not keys_to_fetch:
            return {k: self._changelog_cache.get(k, []) for k in task_keys}

        logger.info(f"Загружаю историю изменений для {len(keys_to_fetch)} задач...")

        def fetch_one(task_key: str) -> tuple:
            """Загружает changelog для одной задачи с retry."""
            url = f"{self._base_url}/issues/{task_key}/changelog"

            for i in range(self._max_retries):
                try:
                    response = self._client.get(url)

                    if response.status_code == 429:
                        time.sleep(2 + random.random())
                        continue

                    response.raise_for_status()
                    return task_key, response.json()

                except httpx.HTTPError:
                    if i == self._max_retries - 1:
                        return task_key, []
                    time.sleep(1)

            return task_key, []

        # Параллельная загрузка
        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            future_to_key = {
                executor.submit(fetch_one, key): key for key in keys_to_fetch
            }

            for i, future in enumerate(as_completed(future_to_key)):
                key, changelog = future.result()
                self._changelog_cache[key] = changelog

                if (i + 1) % 50 == 0:
                    logger.info(f"  ...загружено {i + 1} историй")

        return {k: self._changelog_cache.get(k, []) for k in task_keys}

    def parse_task(self, raw_data: Dict, project_name: str) -> Task:
        """Преобразует сырые данные API в доменную модель Task."""
        created_at = self._parse_datetime(raw_data["createdAt"])
        updated_at = self._parse_datetime(raw_data["updatedAt"])

        resolved_at = None
        if raw_data.get("resolvedAt"):
            resolved_at = self._parse_datetime(raw_data["resolvedAt"])

        parent_key = None
        if raw_data.get("parent"):
            parent_key = raw_data["parent"].get("key")

        return Task(
            key=raw_data["key"],
            summary=raw_data["summary"],
            project=project_name,
            assignee=raw_data.get("assignee", {}).get("display", "Не назначен"),
            status=raw_data["status"]["key"],
            created=created_at,
            updated=updated_at,
            resolved=resolved_at,
            parent_key=parent_key,
            priority=raw_data.get("priority", {}).get("display", ""),
        )

    def parse_status_changes(self, changelog: List[Dict]) -> List[TaskChange]:
        """Извлекает изменения статуса из changelog."""
        changes: List[TaskChange] = []

        for entry in changelog:
            try:
                updated_at = self._parse_datetime(entry["updatedAt"])

                for field in entry.get("fields", []):
                    if field.get("field", {}).get("id") == "status":
                        changes.append(
                            TaskChange(
                                timestamp=updated_at,
                                field="status",
                                old_value=field.get("from", {}).get("key", ""),
                                new_value=field.get("to", {}).get("key", ""),
                            )
                        )
            except (KeyError, ValueError):
                continue

        return sorted(changes, key=lambda x: x.timestamp)

    def _parse_datetime(self, dt_string: str) -> datetime:
        """Парсит строку даты из API."""
        return datetime.fromisoformat(
            dt_string.replace("Z", "+00:00")
        ).replace(tzinfo=None)
