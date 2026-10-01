@echo off
setlocal
cd /d "%~dp0"

title Melody Guitars - запуск

echo ========================================
echo          MELODY GUITARS - ЗАПУСК
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo Установи Python 3.11 или новее и попробуй снова.
    echo При установке Python обязательно отметь "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\python.exe" (
    echo [1/3] Создаю виртуальное окружение...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение.
        echo.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Виртуальное окружение уже существует.
)

echo [2/3] Устанавливаю/проверяю зависимости...
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить зависимости.
    echo.
    pause
    exit /b 1
)

echo [3/3] Запускаю сервер...
echo.
echo Магазин: http://127.0.0.1:8000/
echo Админка: http://127.0.0.1:8000/admin/login
echo API docs: http://127.0.0.1:8000/docs
echo.

start "Melody Guitars Server" cmd /k ""%~dp0venv\Scripts\python.exe" -m uvicorn app.main:app --reload"

timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000/"

endlocal
exit /b 0
