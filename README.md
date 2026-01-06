# Ultimativer Crypto-Signal-Bot

Ein leistungsstarker privater Telegram-Bot, der automatisch alle Bitget USDT-Perpetual Futures scannt und hochwertige Handelssignale erkennt.

## Funktionen

- Automatisches Scanning aller Bitget USDT-Perpetual Futures
- Erkennung von Fibonacci Goldener Schnitt (61,8–78,6 %)
- RSI- und MACD-Divergenzen
- Volume-Pumps
- Order Blocks und Fair Value Gaps
- Professionelle Chart-Bilder im dunklen TradingView-Style
- Klare, informative Nachrichten auf Deutsch

## Installation

1. Stelle sicher, dass Python 3.8+ installiert ist
2. Klone das Repository
3. Installiere die Abhängigkeiten:

```bash
python setup.py
```

Oder manuell:

```bash
python -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Konfiguration

1. Erstelle einen neuen Bot bei @BotFather und kopiere den Token
2. Erstelle einen privaten Kanal oder nutze eine Gruppe
3. Füge den Bot als Administrator hinzu
4. Ermittle die Chat-ID (z.B. mit @getmyid_bot)
5. Trage Token und Chat-ID in der `.env`-Datei ein:

```env
BOT_TOKEN=dein_bot_token_hier
CHAT_ID=deine_chat_id_hier
```

## Starten des Bots

```bash
python run_bot.py
```

## Dateistruktur

- `main.py` - Hauptcode des Bots
- `config.py` - Konfigurationseinstellungen
- `setup.py` - Installationsskript
- `run_bot.py` - Startskript
- `requirements.txt` - Python-Abhängigkeiten
- `.env` - Sensible Konfigurationsdaten (nicht committen!)

## Wie es funktioniert

Der Bot scannt kontinuierlich alle verfügbaren Coins auf Bitget in den Timeframes 15m, 1h und 4h und sucht nach:

- Berührung des goldenen Fibonacci-Schnitts (61,8–78,6 %)
- Bullischen RSI-Divergenzen
- Bullischen MACD-Crossovers in Abwärtstrends
- Volumen-Pumps (über 4x dem Durchschnitt)
- Order Blocks und Fair Value Gaps

Bei Erkennung eines Signals wird ein professioneller Chart erstellt und mit einer detaillierten Nachricht an den konfigurierten Chat gesendet.