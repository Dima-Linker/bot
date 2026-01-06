import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# ================== KONFIGURATION ==================
BOT_TOKEN = os.getenv('BOT_TOKEN', 'DEIN_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID', 'DEINE_CHAT_ID')

SCAN_INTERVAL = 300  # Alle 5 Minuten
TIMEFRAMES = ['15m', '1h', '4h']