@echo off
REM Script para testar todos os dispositivos PIENG
REM - SDM630, Tuya, PZEM-004T, USR-G771

echo ============================================
echo   PIENG - Teste de Todos os Dispositivos
echo ============================================
echo.

REM Verificar se venv existe
if not exist ".venv" (
    echo [AVISO] Ambiente virtual nao encontrado!
    echo Execute primeiro: setup_env.bat
    echo.
    pause
    exit /b 1
)

REM Ativar venv
call .venv\Scripts\activate.bat

REM Executar teste
echo Iniciando teste de dispositivos...
echo.
python test_all_devices.py

echo.
echo ============================================
echo   Teste concluido!
echo ============================================
echo.
pause

