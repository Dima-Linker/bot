#!/usr/bin/env python3
"""
Hauptdatei für den Crypto-Signal Hub-Bot - vereinfachte Version
"""

import os
import asyncio
from telegram.ext import Application
from telegram import Update, BotCommand
from dotenv import load_dotenv

from db.database import init_db
from db.repo import Repo
from scanner.bitget_client import BitgetClient

from modules import volume
from bot.handlers import setup_handlers

# Load environment variables
load_dotenv()

def main():
    """Main entry point with simplified approach"""
    print("🚀 Starte den vereinfachten Crypto-Signal-Bot...")
    
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
    application = Application.builder().token(bot_token).post_init(post_init).build()
    
    # Setup handlers
    print("🔧 Registriere Handler...")
    setup_handlers(application)
    
    print("✅ Bot ist bereit! Warte auf Befehle...")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def post_init(application):
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