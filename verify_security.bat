@echo off
REM Script para verificar segurança antes de commit
REM PIENG Energy - 2025

echo ============================================
echo   PIENG - Verificacao de Seguranca
echo ============================================
echo.

REM Verificar se .env está no .gitignore
findstr /C:".env" .gitignore >nul 2>&1
if errorlevel 1 (
    echo [ERRO] .env NAO esta protegido no .gitignore!
    echo        Adicione ".env" ao arquivo .gitignore
    pause
    exit /b 1
) else (
    echo [OK] .env protegido no .gitignore
)

REM Verificar se .env existe
if exist ".env" (
    echo [OK] Arquivo .env existe
) else (
    echo [AVISO] Arquivo .env nao encontrado
    echo         Copie env.example para .env e configure suas credenciais
)

REM Verificar se .env seria commitado
git check-ignore .env >nul 2>&1
if errorlevel 1 (
    echo [ERRO] .env NAO esta sendo ignorado pelo Git!
    echo        Verifique o .gitignore
    pause
    exit /b 1
) else (
    echo [OK] .env esta sendo ignorado pelo Git
)

REM Verificar se há credenciais em arquivos Python
echo.
echo Verificando por credenciais expostas em codigo...
findstr /S /I "access_id.*=.*\"" *.py >nul 2>&1
if not errorlevel 1 (
    echo [AVISO] Possivel credencial encontrada em codigo Python!
    echo         Revise os arquivos e use dotenv
)

findstr /S /I "secret.*=.*\"" *.py >nul 2>&1
if not errorlevel 1 (
    echo [AVISO] Possivel secret encontrada em codigo Python!
    echo         Revise os arquivos e use dotenv
)

echo.
echo ============================================
echo   Verificacao concluida!
echo ============================================
echo.
echo Antes de fazer commit:
echo   1. Verifique que .env nao esta nos arquivos staged
echo   2. Execute: git status
echo   3. Confirme que .env NAO aparece
echo.
pause


