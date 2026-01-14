@echo off
:: Asegurar que estamos en el directorio del proyecto (donde esta este archivo)
cd /d "%~dp0"

TITLE NotiaBet Launcher
color 0A
cls
echo ==========================================================
echo      🚀 LAUNCHER DE NOTIABET (Backend + Frontend) 🚀
echo ==========================================================
echo.
echo  [1] Verificando entorno...
echo      Directorio: %CD%
echo.

:: 1. Backend Service
echo  [2] Iniciando Backend (Python/FastAPI)...
echo      -> Se abrira una nueva ventana para el servidor.
start "NotiaBet Backend Service" cmd /k "call venv\Scripts\activate && echo Backend running... && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Esperar 3 segundos para dar tiempo al backend
timeout /t 3 /nobreak >nul

:: 2. Mobile App
echo.
echo  [3] Iniciando App Movil (Expo)...
echo      -> Instalando dependencias faltantes para asegurar compatibilidad...
call npm install
echo.
echo      -> Limpiando cache (--clear) para evitar errores.
cd mobile-app
start "NotiaBet Mobile App (QR Code)" cmd /k "mode con: cols=140 lines=50 && npx expo start --clear"

echo.
echo ==========================================================
echo  ✅ SISTEMA INICIADO EXITOSAMENTE
echo ==========================================================
echo.
echo  INSTRUCCIONES:
echo  1. Ve a la ventana titulada "NotiaBet Mobile App".
echo  2. Escanea el codigo QR con tu celular (App Expo Go).
echo  3. Si ves algun error rojo, presiona 'r' en esa ventana.
echo.
pause
