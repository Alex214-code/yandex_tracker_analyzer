# Yandex Tracker Analyzer

REST API сервис для генерации Excel-отчётов по задачам Yandex Tracker.

## Описание

Сервис предназначен для сервис-менеджеров, которым требуется регулярно формировать отчёты для руководства. Предоставляет удобный Swagger UI интерфейс для работы с данными без привлечения программистов.

### Возможности

- **Помесячная разбивка** — одна строка = одна задача в одном месяце
- **Учет статусов** — статус на начало месяца и переходы внутри месяца
- **Логика "Активного пула"** — был в работе на начало или перешел в работу
- **Иерархия задач** — разделы определяются по корневой родительской задаче (Контейнеру)
- **Уровень вложенности** — подсчёт глубины в иерархии
- **onHold → Приостановлено** — автоматическая замена статуса

### Типичный рабочий процесс

1. **Первоначальная настройка** (один раз):
   - Откройте Swagger UI: `http://localhost:8000/docs`
   - Перейдите в раздел "Проекты"
   - Вызовите `GET /projects/available` — получите список всех доступных проектов
   - Выберите нужные проекты и сохраните их через `PUT /projects/default`

2. **Ежемесячная генерация отчёта**:
   - Откройте Swagger UI
   - Перейдите к `POST /reports/generate`
   - Укажите период (например: октябрь-ноябрь 2025)
   - Нажмите "Execute" и скачайте готовый Excel-файл
   - Отправьте файл руководству

3. **Управление проектами**:
   - Добавить проект: `POST /projects/default/add`
   - Удалить проект: `POST /projects/default/remove`
   - Сбросить к настройкам из .env: `DELETE /projects/default`

**Преимущество**: После первоначальной настройки для генерации отчёта достаточно указать только период — список проектов сохраняется между сессиями.

## Архитектура

Проект построен на **гексагональной архитектуре** (Ports & Adapters):

```
src/
├── adapters/
│   ├── primary/
│   │   └── web/              # FastAPI роутеры и схемы
│   └── secondary/
│       ├── tracker_api/      # Адаптер Yandex Tracker API
│       ├── excel_export/     # Адаптер экспорта в Excel
│       └── user_settings/    # Адаптер пользовательских настроек
├── core/
│   ├── application/
│   │   ├── ports/            # Интерфейсы для адаптеров
│   │   └── use_cases/        # Бизнес-сценарии
│   └── domain/
│       ├── models/           # Доменные модели
│       └── services/         # Доменные сервисы
├── entrypoints/
│   └── run.py                # Точка входа
├── container.py              # DI контейнер
└── settings.py               # Настройки
```

## Установка

### Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Alex214-code/yandex_tracker_analyzer.git
cd yandex_tracker_analyzer
```

2. Установите Poetry:
```bash
pip install poetry
```

3. Установите зависимости:
```bash
poetry install
```

4. Создайте файл `.env` (см. `.env.example`):
```bash
# Linux/macOS
cp .env.example .env

# Windows CMD
copy .env.example .env
```
Заполните файл реальными значениями.

5. Запустите сервер:
```bash
poetry run python -m src.entrypoints.run
```

### Docker

1. Клонируйте репозиторий:
```bash
git clone https://github.com/Alex214-code/yandex_tracker_analyzer.git
cd yandex_tracker_analyzer
```

2. Соберите и запустите:
```bash
# Сборка образа
docker build -t yandex-tracker-analyzer .

# Запуск контейнера
docker run -d \
  --name tracker-analyzer \
  -p 8000:8000 \
  --env-file .env \
  yandex-tracker-analyzer
```

## API

### Endpoints

#### Система

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/health` | Проверка здоровья сервиса |

#### Проекты

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/projects/available` | Все доступные проекты |
| GET | `/projects/default` | Текущий список проектов по умолчанию |
| PUT | `/projects/default` | Установить новый список проектов |
| POST | `/projects/default/add` | Добавить проект в список |
| POST | `/projects/default/remove` | Удалить проект из списка |
| DELETE | `/projects/default` | Сбросить к настройкам из .env |

#### Отчёты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/reports/generate` | Генерация Excel-отчёта |
| POST | `/reports/generate/status` | Проверка параметров без генерации |

### Примеры запросов

#### Получение всех доступных проектов

```bash
curl -X GET "http://localhost:8000/projects/available"
```

Вернёт список:
```json
{
  "values": [
    "НорНикель НОФ (Тех. Поддержка)",
    "УГМК Святогор (Тех. Поддержка)"
  ],
  "total": 2
}
```

#### Установка проектов по умолчанию

```bash
curl -X PUT "http://localhost:8000/projects/default" \
  -H "Content-Type: application/json" \
  -d '{
    "projects": ["Проект А (Тех. Поддержка)", "Проект Б (Тех. Поддержка)"]
  }'
```

#### Генерация отчёта

```bash
curl -X POST "http://localhost:8000/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "start_year": 2025,
    "start_month": 10,
    "end_year": 2025,
    "end_month": 11
  }' \
  --output report.xlsx
```

## Переменные окружения

| Переменная | Описание | По умолчанию | Обязательная |
|------------|----------|--------------|--------------|
| `YANDEX_CLIENT_ID` | Client ID приложения Yandex OAuth | — | Да |
| `YANDEX_OAUTH_TOKEN` | OAuth токен для Yandex Tracker API | — | Да |
| `YANDEX_ORG_ID` | ID организации в Yandex Tracker | — | Да |
| `TRACKER_API_BASE_URL` | Базовый URL API | `https://api.tracker.yandex.net/v2` | Нет |
| `API_TIMEOUT` | Таймаут запросов (сек) | `30` | Нет |
| `API_MAX_RETRIES` | Макс. повторных попыток | `3` | Нет |
| `API_MAX_WORKERS` | Потоков для параллельных запросов | `5` | Нет |
| `TARGET_PROJECTS` | JSON-список проектов по умолчанию | См. ниже | Нет |
| `HOST` | Хост сервера | `0.0.0.0` | Нет |
| `PORT` | Порт сервера | `8000` | Нет |
| `WORKERS` | Количество воркеров uvicorn | `1` | Нет |
| `DEBUG` | Режим отладки | `false` | Нет |
| `LOG_LEVEL` | Уровень логирования | `INFO` | Нет |
| `LOG_FORMAT` | Формат логов (`json`/`text`) | `json` | Нет |

## Проекты по умолчанию

Если `TARGET_PROJECTS` не указан в `.env`, используются встроенные значения:

```json
[
  "НорНикель НОФ (Тех. Поддержка)",
  "УГМК Святогор (Тех. Поддержка)",
  "УГМК Гайский ГОК (Тех. Поддержка)",
  "РМК Томинский ГОК (Тех. Поддержка)"
]
```

Чтобы получить актуальный список всех доступных проектов, используйте `GET /projects/available`.

## Хранение пользовательских настроек

Настройки проектов сохраняются в файле `user_settings.json` в рабочей директории. Файл создаётся автоматически при первом вызове `PUT /projects/default`.

**Приоритет источников:**
1. Явно указанные в запросе `/reports/generate` (параметр `projects`)
2. Сохранённые через `/projects/default` (файл `user_settings.json`)
3. Настройки из переменной окружения `TARGET_PROJECTS`
4. Встроенные значения по умолчанию (см. выше)

## Структура Excel отчёта

### Лист "Все_Задачи"

Полный реестр задач с полями:
- Ключ, Ссылка, Заголовок
- Проект, Раздел, Уровень вложенности
- Исполнитель, Приоритет
- Статус на 1 число, Текущий статус
- Флаги: Был в "Открыт", "В работе", "Приостановлено", "Требуется инфо"
- Закрыта в этом месяце
- Даты первого/последнего перехода в каждый статус

### Лист "Анализ_В_Работе"

| Поле | Описание |
|------|----------|
| В работе (на начало) | Задачи в статусе "В работе" на 1 число |
| Пришло в работу | Перешли в "В работе" в течение месяца |
| Всего активных (пул) | Сумма двух предыдущих |
| Выполнено из пула | Закрыто из активных |
| Остаток в работе | Активные минус выполненные |

### Лист "Сводная_по_разделам"

Статистика по контейнерам/эпикам.

### Лист "Статусы_на_1_число"

Распределение задач по статусам на начало каждого месяца.

## Разработка

### Запуск тестов

```bash
poetry run pytest
```

### Линтинг

```bash
poetry run ruff check src/
poetry run mypy src/
```

### Pre-commit хуки

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## CI/CD

### Сборка Docker образа

```bash
docker build -t yandex-tracker-analyzer:$(git rev-parse --short HEAD) .
```

### Запуск в production

```bash
docker run -d \
  --name tracker-analyzer \
  --restart unless-stopped \
  -p 8000:8000 \
  -e YANDEX_CLIENT_ID=xxx \
  -e YANDEX_OAUTH_TOKEN=xxx \
  -e YANDEX_ORG_ID=xxx \
  -e LOG_FORMAT=json \
  -e WORKERS=4 \
  yandex-tracker-analyzer:latest
```

## Логирование

- Логи пишутся в stdout в структурированном JSON формате
- Включают PID процесса для идентификации воркера
- Уровень логирования настраивается через `LOG_LEVEL`

## Лицензия

Внутренний проект компании.
