@echo off
echo 🚀 Starte den ultimativen Crypto-Signal-Bot...

REM Überprüfe, ob Python installiert ist
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python ist nicht installiert. Bitte installiere Python 3.8+ zuerst.
    pause
    exit /b 1
)

REM Erstelle virtuelle Umgebung, falls sie nicht existiert
if not exist "venv" (
    echo 🔧 Erstelle virtuelle Umgebung...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Fehler bei der Erstellung der virtuellen Umgebung
        pause
        exit /b 1
    )
    echo ✅ Virtuelle Umgebung erstellt
)

REM Aktiviere die virtuelle Umgebung und starte den Bot
echo ✅ Aktiviere virtuelle Umgebung und starte den Bot...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Fehler bei der Aktivierung der virtuellen Umgebung
    pause
    exit /b 1
)

REM Installiere Abhängigkeiten, falls nicht vorhanden
echo 📦 Installiere Abhängigkeiten...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Fehler bei der Installation der Abhängigkeiten
    pause
    exit /b 1
)

REM Starte den Bot
echo 🚀 Starte den Bot...
python run_bot.py

pause