# Мелодия Гитар

Небольшой интернет-магазин музыкальных инструментов на FastAPI + SQLAlchemy с публичным каталогом и простой админ-панелью.

## Локальный запуск на Windows

1. Откройте папку проекта в терминале.
2. Создайте виртуальное окружение:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Проверьте `.env`. Для локальной работы можно использовать SQLite по умолчанию.

5. Запустите:

```bash
uvicorn app.main:app --reload
```

Магазин: http://127.0.0.1:8000/
Документация API: http://127.0.0.1:8000/docs
Админка: http://127.0.0.1:8000/admin/login

## Render + PostgreSQL

Проект поддерживает Render Postgres через переменную `DATABASE_URL`.

### Web Service

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Environment Variables

```text
ADMIN_PASSWORD=ваш_пароль
SECRET_KEY=длинная_случайная_строка
DATABASE_URL=<Internal Database URL от Render Postgres>
SEED_DEMO_DATA=true
MAX_UPLOAD_MB=5
```

Код автоматически преобразует `postgres://` / `postgresql://` в формат SQLAlchemy с драйвером `psycopg`.

Важно: Web Service и Postgres должны быть в одном регионе, чтобы приложение использовало внутреннее соединение Render. Render рекомендует Internal Database URL для Render-сервисов в том же регионе. 

Free Render Postgres сейчас имеет лимит 1 GB и автоматически истекает через 30 дней. Для постоянного проекта нужен платный план. 

### Данные

При первом запуске пустая PostgreSQL-база автоматически создаётся через SQLAlchemy и заполняется 6 категориями и 8 демонстрационными товарами, если `SEED_DEMO_DATA=true`.

`melody.db` из локальной версии не импортируется автоматически: это отдельная SQLite-база. Для Render PostgreSQL стартовые товары создаются seed-скриптом.

## Админка

- категории: создание, редактирование, удаление, иконка и фото;
- товары: создание, редактирование, удаление, фото, цена, описание, характеристики и наличие;
- заказы: просмотр состава и изменение статуса;
- загружаемые изображения проверяются через Pillow и сохраняются в `app/static/uploads/` под случайными именами.

## Важный нюанс про фотографии

Render Postgres сохраняет данные базы, но не файлы, которые приложение пишет на локальный диск. Загруженные через админку изображения требуют отдельного постоянного хранилища (например, object storage) или persistent disk на платном Web Service.

Демонстрационные изображения используют внешние URL Unsplash.

## Быстрый запуск Windows

Запусти `start.bat` двойным кликом. Он создаст `venv`, установит зависимости, запустит FastAPI и откроет магазин в браузере.
