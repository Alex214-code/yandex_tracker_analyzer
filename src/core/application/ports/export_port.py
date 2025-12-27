"""
Порт для экспорта отчётов в Excel.

Определяет интерфейс для сохранения отчётов в формате Excel.
"""

from abc import ABC, abstractmethod

from src.core.domain.models import Report


class ExportPort(ABC):
    """
    Абстрактный порт для экспорта отчётов в Excel.

    Адаптер должен реализовать этот интерфейс для сохранения
    данных в формате Excel (.xlsx).
    """

    @abstractmethod
    def export_to_bytes(self, report: Report) -> bytes:
        """
        Экспортирует отчёт в байтовый поток.

        Args:
            report: Объект отчёта с данными и сводными таблицами.

        Returns:
            Байтовое представление файла отчёта.
        """
        pass

    @abstractmethod
    def export_to_file(self, report: Report, filepath: str) -> None:
        """
        Экспортирует отчёт в файл.

        Args:
            report: Объект отчёта с данными и сводными таблицами.
            filepath: Путь к файлу для сохранения.
        """
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """
        Возвращает MIME-тип для формата экспорта.

        Returns:
            MIME-тип (например, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet").
        """
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """
        Возвращает расширение файла для формата экспорта.

        Returns:
            Расширение файла (например, ".xlsx").
        """
        pass
