#!/bin/bash

echo "🚀 Installation des ultimativen Crypto-Signal-Bots..."

# Überprüfe, ob Python 3 installiert ist
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 ist nicht installiert. Bitte installiere Python3 zuerst."
    exit 1
fi

# Überprüfe, ob pip installiert ist
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 ist nicht installiert. Bitte installiere pip3 zuerst."
    exit 1
fi

echo "✅ Python3 und pip3 sind installiert"

# Erstelle virtuelle Umgebung, falls sie nicht existiert
if [ ! -d "venv" ]; then
    echo "🔧 Erstelle virtuelle Umgebung..."
    python3 -m venv venv
    echo "✅ Virtuelle Umgebung erstellt"
else
    echo "✅ Virtuelle Umgebung existiert bereits"
fi

# Aktiviere die virtuelle Umgebung und installiere Abhängigkeiten
echo "📦 Installiere Python-Abhängigkeiten..."
source venv/bin/activate && pip install --upgrade pip
source venv/bin/activate && pip install -r requirements.txt

echo "✅ Abhängigkeiten installiert"

# Installiere python-dotenv separat, falls nicht in requirements.txt
source venv/bin/activate && pip install python-dotenv

echo "✅ Zusätzliche Abhängigkeiten installiert"

echo "🎉 Installation abgeschlossen!"
echo ""
echo "So startest du den Bot:"
echo "1. Aktiviere die virtuelle Umgebung: source venv/bin/activate"
echo "2. Bearbeite die .env-Datei mit deinem Bot-Token und Chat-ID"
echo "3. Starte den Bot: python main.py"