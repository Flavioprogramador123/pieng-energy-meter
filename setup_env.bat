@echo off
REM Script para configurar ambiente virtual no Windows
REM PIENG Energy Monitor - 2025

echo ============================================
echo   PIENG - Setup Ambiente Virtual
echo ============================================
echo.

REM Verificar se Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python de: https://python.org
    pause
    exit /b 1
)

REM Criar venv se não existir
if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
    echo [OK] Ambiente virtual criado!
) else (
    echo [OK] Ambiente virtual ja existe!
)

echo.
echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo.
echo Atualizando pip...
python -m pip install --upgrade pip --quiet

echo.
echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo ============================================
echo   [OK] Setup concluido com sucesso!
echo ============================================
echo.
echo Proximos passos:
echo   1. Execute: test_all_devices.bat
echo   2. Configure suas credenciais Tuya
echo   3. Teste seus dispositivos
echo.
pause

