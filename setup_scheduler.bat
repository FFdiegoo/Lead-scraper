@echo off
:: ============================================================
::  Full Force AI - Lead Scraper
::  Windows Task Scheduler Setup
::  Rechtermuisknop -> Als administrator uitvoeren
:: ============================================================

set SCRIPT_DIR=%~dp0
set PYTHON=%SCRIPT_DIR%.venv\Scripts\python.exe

:: Controleer of de venv bestaat
if not exist "%PYTHON%" (
    echo FOUT: .venv niet gevonden. Voer eerst uit:
    echo   python -m venv .venv
    echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%logs" mkdir "%SCRIPT_DIR%logs"

echo Aanmaken van geplande taken...
echo.

:: Taak 1: Dagelijkse scraper om 08:00
schtasks /create ^
    /tn "FFAI_LeadScraper" ^
    /tr "\"%PYTHON%\" \"%SCRIPT_DIR%main.py\" >> \"%SCRIPT_DIR%logs\scraper.log\" 2>&1" ^
    /sc DAILY /st 08:00 /f /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo [OK] FFAI_LeadScraper aangemaakt - dagelijks om 08:00
) else (
    echo [FOUT] Kon FFAI_LeadScraper niet aanmaken.
)

:: Taak 2: Dagelijkse email sender om 09:30
schtasks /create ^
    /tn "FFAI_EmailSender" ^
    /tr "\"%PYTHON%\" \"%SCRIPT_DIR%send_emails.py\" >> \"%SCRIPT_DIR%logs\email.log\" 2>&1" ^
    /sc DAILY /st 09:30 /f /rl HIGHEST

if %ERRORLEVEL% EQU 0 (
    echo [OK] FFAI_EmailSender aangemaakt - dagelijks om 09:30
) else (
    echo [FOUT] Kon FFAI_EmailSender niet aanmaken.
)

echo.
echo ============================================================
echo  Klaar! Beheer via: Taakplanner (taskschd.msc)
echo ============================================================
echo.
pause
