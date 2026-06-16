@echo off
:: ============================================================
::  Full Force AI — Lead Scraper
::  Windows Task Scheduler Setup
::  Voer dit script uit als Administrator (rechtermuisknop → Als administrator uitvoeren)
:: ============================================================

set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python

:: Controleer of Python beschikbaar is
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo FOUT: Python niet gevonden. Zorg dat Python in je PATH staat.
    pause
    exit /b 1
)

:: Maak logs map aan als die niet bestaat
if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo Aanmaken van geplande taken...
echo.

:: ── Taak 1: Dagelijkse scraper om 08:00 ─────────────────────────────────────
schtasks /create ^
    /tn "FFAI_LeadScraper" ^
    /tr "\"%PYTHON_PATH%\" \"%SCRIPT_DIR%main.py\" >> \"%SCRIPT_DIR%logs\scraper.log\" 2>&1" ^
    /sc DAILY ^
    /st 08:00 ^
    /f ^
    /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo [OK] Taak aangemaakt: FFAI_LeadScraper — dagelijks om 08:00
) else (
    echo [FOUT] Kon FFAI_LeadScraper niet aanmaken. Draai als Administrator?
)

echo.

:: ── Taak 2: Dagelijkse email verzender om 09:30 ──────────────────────────────
schtasks /create ^
    /tn "FFAI_EmailSender" ^
    /tr "\"%PYTHON_PATH%\" \"%SCRIPT_DIR%send_emails.py\" >> \"%SCRIPT_DIR%logs\email.log\" 2>&1" ^
    /sc DAILY ^
    /st 09:30 ^
    /f ^
    /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo [OK] Taak aangemaakt: FFAI_EmailSender — dagelijks om 09:30
) else (
    echo [FOUT] Kon FFAI_EmailSender niet aanmaken. Draai als Administrator?
)

echo.
echo ============================================================
echo  Taken aangemaakt! Je kunt ze beheren via:
echo  Taakbeheer (Task Scheduler) → Taakplannerbibliotheek
echo ============================================================
echo.
echo  Handmatig testen:
echo    python main.py
echo    python send_emails.py
echo.
pause
