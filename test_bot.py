#!/usr/bin/env python3
"""
Einfacher Test-Bot um die grundlegende Funktionalität zu überprüfen
"""

import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import Update
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def start(update, context):
    """Send a test message when the command /start is issued."""
    await update.message.reply_text('Hello! Bot is working!')
    print("DEBUG: /start command received")

async def echo(update, context):
    """Echo the user message."""
    await update.message.reply_text(update.message.text)
    print(f"DEBUG: Echo message received: {update.message.text}")

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    TOKEN = os.getenv("BOT_TOKEN")
    if not TOKEN:
        print("❌ Kein Bot-Token gefunden!")
        return
    
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Run the bot until you press Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()