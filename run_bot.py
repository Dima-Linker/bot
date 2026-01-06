#!/usr/bin/env python3
"""
Startskript für den ultimativen Crypto-Signal-Bot mit modularer Architektur
"""

import os
import sys
import asyncio
import time
from datetime import datetime
from dotenv import load_dotenv

from db.database import init_db
from db.repo import Repo
from scanner.scheduler import scheduler_loop
from scanner.runner import run_scan_for_user
from scanner.bitget_client import BitgetClient

from modules import volume

# Load environment variables
load_dotenv()

def telegram_send_fn(chat_id: str, text: str, **kwargs):
    """Send message via python-telegram-bot"""
    import telegram
    from telegram.ext import Application
    
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ Kein Bot-Token gefunden. Nachricht kann nicht gesendet werden.")
        print(f"Nachricht an {chat_id}: {text}")
        return
    
    async def send_message():
        try:
            app = Application.builder().token(bot_token).build()
            async with app:
                chart_path = kwargs.pop('chart_path', None)
                parse_mode = kwargs.pop('parse_mode', None)
                if chart_path and os.path.exists(chart_path):
                    # Send chart as photo with caption
                    with open(chart_path, 'rb') as chart_file:
                        await app.bot.send_photo(
                            chat_id=chat_id,
                            photo=chart_file,
                            caption=text[:1024],  # Telegram caption limit
                            parse_mode=parse_mode,
                            **kwargs
                        )
                else:
                    # Send text message only
                    await app.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, **kwargs)
                print(f"✅ Nachricht erfolgreich an {chat_id} gesendet")
        except Exception as e:
            print(f"❌ Fehler beim Senden der Nachricht: {e}")
    
    # Run the async function
    try:
        asyncio.run(send_message())
    except RuntimeError:
        # Falls es Probleme mit dem Event Loop gibt
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, send_message())
            future.result()


def main():
    conn = init_db('./data/bot.db', './db/schema.sql')
    repo = Repo(conn)

    bitget = BitgetClient(base_url='https://api.bitget.com')

    modules_registry = {
        'volume': volume,
        # später: 'fibo': fibo, 'rsi_div': rsi_div, 'macd': macd, 'smc': smc
    }

    def scan_all_users():
        # MVP: erstmal nur du (später: aus DB alle user laden)
        users = [os.getenv("CHAT_ID", "<DEIN_TG_USER_ID>")]  # Changed to use CHAT_ID from .env
        for u in users:
            if u and u != "<DEIN_TG_USER_ID>":
                run_scan_for_user(repo, u, bitget, telegram_send_fn, modules_registry)

    scheduler_loop(scan_all_users, interval_seconds=300)


if __name__ == '__main__':
    main()