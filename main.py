#!/usr/bin/env python3
"""
Hauptdatei für den Crypto-Signal Hub-Bot
Kombiniert Telegram-Bot-Handler mit dem Scanner-System
"""

import os
import asyncio
from telegram.ext import Application
from telegram import Update, BotCommand
from dotenv import load_dotenv

from db.database import init_db
from db.repo import Repo
from scanner.scheduler import scheduler_loop
from scanner.runner import run_scan_for_user
from scanner.bitget_client import BitgetClient

# Import aller Module
from modules import volume
from modules import fibonacci
from modules import rsi_divergence
from modules import macd
from modules import smc
from bot.handlers import setup_handlers

# Load environment variables
load_dotenv()

def main():
    """Main entry point with both bot and scanner"""
    print("🚀 Starte den ultimativen Crypto-Signal Hub-Bot mit Scanner...")
    
    # Initialize database
    conn = init_db('./data/bot.db', './db/schema.sql')
    scanner_repo = Repo(conn)
    print("✅ Datenbank initialisiert")

    # Initialize Bitget client
    scanner_bitget = BitgetClient(base_url='https://api.bitget.com')
    print("✅ Bitget Client initialisiert")

    # Initialize Telegram bot application
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        print("❌ Kein Telegram Bot Token in .env gefunden.")
        return
    
    print("🔧 Initialisiere Telegram Bot...")
    application = Application.builder().token(bot_token).post_init(lambda app: post_init(app, scanner_repo, scanner_bitget)).build()
    
    # Setup handlers
    print("🔧 Registriere Handler...")
    setup_handlers(application)
    
    # Start scanner in background thread
    import threading
    def start_scanner():
        def scan_all_users():
            # MVP: erstmal nur du (später: aus DB alle user laden)
            users = [os.getenv("CHAT_ID", "<DEIN_TG_USER_ID>")]  # Changed from TELEGRAM_CHAT_ID to CHAT_ID to match .env
            for u in users:
                if u and u != "<DEIN_TG_USER_ID>":
                    def telegram_send_fn(chat_id: str, text: str, **kwargs):
                        """Send message via Telegram bot"""
                        # Extract optional chart_path from kwargs
                        chart_path = kwargs.pop('chart_path', None)
                        
                        # Actually send the message
                        async def send_msg():
                            try:
                                if chart_path and os.path.exists(chart_path):
                                    # Send chart with caption
                                    with open(chart_path, 'rb') as chart_file:
                                        await application.bot.send_photo(
                                            chat_id=chat_id, 
                                            photo=chart_file,
                                            caption=text
                                        )
                                else:
                                    # Send text message only
                                    await application.bot.send_message(chat_id=chat_id, text=text, **kwargs)
                                print(f"✅ Nachricht erfolgreich an {chat_id} gesendet")
                            except Exception as e:
                                print(f"❌ Fehler beim Senden der Nachricht: {e}")
                        
                        # Run the async function in a new event loop
                        import threading
                        def run_in_thread():
                            try:
                                import asyncio
                                asyncio.run(send_msg())
                            except RuntimeError as e:
                                print(f"Fehler im Nachrichtenversand-Thread: {e}")
                        
                        thread = threading.Thread(target=run_in_thread)
                        thread.start()
                    
                    # Register all modules
                    modules_registry = {
                        'volume': volume,
                        'fibonacci': fibonacci,
                        'rsi_divergence': rsi_divergence,
                        'macd': macd,
                        'smc': smc
                    }
                    
                    run_scan_for_user(scanner_repo, u, scanner_bitget, telegram_send_fn, modules_registry)
        
        scheduler_loop(scan_all_users, interval_seconds=300)
    
    scanner_thread = threading.Thread(target=start_scanner, daemon=True)
    scanner_thread.start()
    print("✅ Scanner gestartet")
    
    print("✅ Bot ist bereit! Warte auf Befehle und scannt Märkte...")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def post_init(application, scanner_repo, scanner_bitget):
    """Register bot commands after the application is initialized"""
    commands = [
        BotCommand("start", "Startmenü öffnen"),
        BotCommand("modules", "Module aktivieren/deaktivieren"),
        BotCommand("combo", "Combo/Premium Einstellungen"),
        BotCommand("watchlist", "Watchlist verwalten"),
        BotCommand("preset", "Konservativ/Normal/Aggressiv"),
        BotCommand("stats", "Statistik & Verlauf"),
        BotCommand("help", "Hilfe / Anleitung"),
        BotCommand("add_symbol", "Füge Symbol zur Watchlist hinzu"),
        BotCommand("remove_symbol", "Entferne Symbol von der Watchlist"),
        BotCommand("menu", "Hauptmenü öffnen")
    ]
    await application.bot.set_my_commands(commands)
    print("✅ Bot commands registriert")


if __name__ == '__main__':
    main()