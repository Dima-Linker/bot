#!/usr/bin/env python3
"""
Testskript zum Senden einer Testnachricht vom Signal-Bot
"""

import asyncio
from telegram import Bot
from config import BOT_TOKEN, CHAT_ID

async def send_test_signal():
    """Sende eine Testnachricht vom Bot"""
    bot = Bot(token=BOT_TOKEN)
    
    test_text = "🧪 TEST-SIGNAL\n\nDies ist eine Testnachricht vom ultimativen Signal-Bot.\n\n✅ Bot ist voll funktionsfähig\n✅ Nachrichten werden korrekt gesendet\n✅ Bereit für den Handel! 🚀"
    
    try:
        await bot.send_message(chat_id=CHAT_ID, text=test_text)
        print("✅ Testnachricht erfolgreich gesendet!")
    except Exception as e:
        print(f"❌ Fehler beim Senden der Testnachricht: {e}")

if __name__ == "__main__":
    print("Sende Testnachricht...")
    asyncio.run(send_test_signal())