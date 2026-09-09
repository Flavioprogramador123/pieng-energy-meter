@echo off
REM Script para iniciar projeto PIENG rapidamente
REM Execute este arquivo toda vez que for trabalhar!

echo ============================================
echo   PIENG Energy - Iniciar Projeto
echo ============================================
echo.

cd /d %~dp0

REM Verificar se ambiente existe
if not exist ".venv" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Execute primeiro: setup_env.bat
    pause
    exit /b 1
)

echo Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo.
echo O que deseja fazer?
echo.
echo 1. Iniciar Backend (Dashboard)
echo 2. Testar Dispositivos
echo 3. Gerar Dados de Teste
echo 4. Verificar Seguranca
echo 5. Ver Documentacao
echo 6. Sair
echo.

choice /C 123456 /N /M "Escolha uma opcao: "

if errorlevel 6 goto :end
if errorlevel 5 goto :docs
if errorlevel 4 goto :security
if errorlevel 3 goto :generate
if errorlevel 2 goto :test
if errorlevel 1 goto :backend

:backend
echo.
echo Iniciando backend...
echo Dashboard em: http://localhost:8000/api/dashboard
echo API Docs em: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --reload --port 8000
goto :end

:test
echo.
python test_all_devices.py
pause
goto :end

:generate
echo.
python generate_test_data.py
pause
goto :end

:security
echo.
call verify_security.bat
goto :end

:docs
echo.
echo Documentacao disponivel:
echo   - SESSAO_18OUT2025.md (resumo de hoje!)
echo   - ANALISE_COMPLETA_SISTEMAS.md (visao geral)
echo   - COMO_TESTAR_DISPOSITIVOS.md (tutorial)
echo   - GLOSSARIO_CLIPPER_PYTHON.md (traducao conceitos)
echo.
start SESSAO_18OUT2025.md
pause
goto :end

:end
echo.
echo Ate a proxima!


