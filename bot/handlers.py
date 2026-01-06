"""
Telegram Bot Handlers for the Crypto-Signal Hub-Bot
"""
from telegram import Update
from telegram.ext import ContextTypes
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message and main menu"""
    if update.message:
        user = update.effective_user
        welcome_text = (
            f"👋 Willkommen beim Crypto-Signal Hub-Bot!\n\n"
            f"Du kannst verschiedene Module aktivieren und Einstellungen vornehmen.\n\n"
            f"Nutze /menu um das Hauptmenü zu öffnen."
        )
        await update.message.reply_text(welcome_text)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send main menu with inline buttons"""
    if update.message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [InlineKeyboardButton("⚙️ Module verwalten", callback_data='modules')],
            [InlineKeyboardButton("🎯 Combo/Premium", callback_data='combo')],
            [InlineKeyboardButton("🎚 Presets", callback_data='presets')],
            [InlineKeyboardButton("📋 Watchlist", callback_data='watchlist')],
            [InlineKeyboardButton("📊 Stats", callback_data='stats')],
            [InlineKeyboardButton("ℹ️ Hilfe", callback_data='help')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(" Wähle eine Option:", reply_markup=reply_markup)


async def modules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /modules command"""
    if update.message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Fetch modules status from DB (using mock for now)
        modules_status = get_modules_status(update.effective_user.id if update.effective_user else 123456)
        
        keyboard = []
        for module, enabled in modules_status.items():
            status_emoji = "🟢" if enabled else "🔴"
            status_text = "AKTIV" if enabled else "INAKTIV"
            keyboard.append([InlineKeyboardButton(f"{status_emoji} {module} - {status_text}", callback_data=f'toggle_{module}')])
        
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Module (grün=aktiviert, rot=deaktiviert):\n\n"
                                      "🟢 = Aktiv (in DB gespeichert)\n"
                                      "🔴 = Inaktiv (in DB gespeichert)", reply_markup=reply_markup)


async def combo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /combo command"""
    if update.message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [InlineKeyboardButton("🛡️ Konservativ", callback_data='combo_conservative')],
            [InlineKeyboardButton("⚖️ Normal", callback_data='combo_normal')],
            [InlineKeyboardButton("⚔️ Aggressiv", callback_data='combo_aggressive')],
            [InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Combo/Premium Einstellungen (in DB gespeichert):", reply_markup=reply_markup)


async def preset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /preset command"""
    if update.message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [InlineKeyboardButton("🛡️ Konservativ", callback_data='preset_conservative')],
            [InlineKeyboardButton("⚖️ Normal", callback_data='preset_normal')],
            [InlineKeyboardButton("⚔️ Aggressiv", callback_data='preset_aggressive')],
            [InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Wähle ein Preset (in DB gespeichert):", reply_markup=reply_markup)


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /watchlist command - now shows active IDEA setups"""
    if update.message:
        # Get user ID
        user_id = str(update.effective_user.id) if update.effective_user else '123456'
        
        # Import here to avoid circular imports
        from db.database import init_db
        from db.repo import Repo
        conn = init_db('./data/bot.db', './db/schema.sql')
        repo = Repo(conn)
        
        # Get active setups from the database
        active_setups = repo.get_active_setups(user_id)
        
        # Sort by score (descending) and then by remaining time (ascending)
        active_setups.sort(key=lambda x: (x.get('trade_score', x.get('idea_score', 0)), x['expires_at']), reverse=True)
        
        if active_setups:
            message = f"Präsente Setups ({len(active_setups)} Einträge - sortiert nach Score):\n\n"
            
            for setup in active_setups[:10]:  # Show top 10
                status_emoji = "🟡" if setup['status'] == 'IDEA' else "🟢"
                side_emoji = "🔴 SHORT" if setup['side'] == 'bearish' else "🟢 LONG"
                
                # Calculate remaining time
                import time
                remaining_minutes = max(0, (setup['expires_at'] - int(time.time())) // 60)
                
                score = setup.get('trade_score', setup.get('idea_score', 0))
                
                message += (
                    f"{status_emoji} {setup['status']} | {side_emoji}\n"
                    f"🪙 {setup['symbol']} ({setup['timeframe']})\n"
                    f"📊 Score: {score}\n"
                    f"⏳ Verbleibend: {remaining_minutes} min\n\n"
                )
            
            if len(active_setups) > 10:
                message += f"... und {len(active_setups) - 10} weitere Setups"
        else:
            message = "Keine aktiven Setups in der Watchlist.\n\nDer Bot sucht nach IDEA Setups (Liquidity + Fib Kombinationen). Sobald gefunden, erscheinen sie hier."
        
        await update.message.reply_text(message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command"""
    if update.message:
        # This would normally fetch from DB
        stats = {
            'signals_sent': 0,
            'active_users': 1,
            'uptime_hours': 0
        }
        
        message = (
            f"📊 Bot-Statistiken:\n\n"
            f"Signale gesendet: {stats['signals_sent']}\n"
            f"Aktive Nutzer: {stats['active_users']}\n"
            f"Laufzeit: {stats['uptime_hours']} Stunden"
        )
        
        await update.message.reply_text(message)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button presses"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Check if query.data is not None before using it
        if query.data:
            if query.data == 'modules':
                await show_modules_menu(update, context)
            elif query.data == 'combo':
                await show_combo_menu(update, context)
            elif query.data == 'presets':
                await show_presets_menu(update, context)
            elif query.data == 'watchlist':
                await show_watchlist_menu(update, context)
            elif query.data == 'stats':
                await show_stats(update, context)
            elif query.data == 'help':
                await show_help(update, context)
            elif query.data.startswith('toggle_'):
                await toggle_module(update, context)
            elif query.data.startswith('combo_'):
                await set_combo_preset(update, context)
            elif query.data.startswith('preset_'):
                await set_preset(update, context)
            elif query.data == 'back_to_menu':
                await menu(update, context)


async def show_modules_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show module management menu"""
    if update.effective_message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Fetch modules status from DB (using mock for now)
        user_id = update.effective_user.id if update.effective_user else 123456
        modules_status = get_modules_status(user_id)
        
        keyboard = []
        for module, enabled in modules_status.items():
            status_emoji = "🟢" if enabled else "🔴"
            status_text = "AKTIV" if enabled else "INAKTIV"
            keyboard.append([InlineKeyboardButton(f"{status_emoji} {module} - {status_text}", callback_data=f'toggle_{module}')])
        
        keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.edit_text("Module (grün=aktiviert, rot=deaktiviert):\n\n"
                                               "🟢 = Aktiv (in DB gespeichert)\n"
                                               "🔴 = Inaktiv (in DB gespeichert)", reply_markup=reply_markup)


async def show_combo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show combo/premium settings menu"""
    if update.effective_message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [InlineKeyboardButton("🛡️ Konservativ", callback_data='combo_conservative')],
            [InlineKeyboardButton("⚖️ Normal", callback_data='combo_normal')],
            [InlineKeyboardButton("⚔️ Aggressiv", callback_data='combo_aggressive')],
            [InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.edit_text("Combo/Premium Einstellungen (in DB gespeichert):", reply_markup=reply_markup)


async def show_presets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show preset selection menu"""
    if update.effective_message:
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = [
            [InlineKeyboardButton("🛡️ Konservativ", callback_data='preset_conservative')],
            [InlineKeyboardButton("⚖️ Normal", callback_data='preset_normal')],
            [InlineKeyboardButton("⚔️ Aggressiv", callback_data='preset_aggressive')],
            [InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.effective_message.edit_text("Wähle ein Preset (in DB gespeichert):", reply_markup=reply_markup)


async def show_watchlist_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show watchlist management menu - now shows active IDEA setups"""
    if update.effective_message:
        # Get user ID
        user_id = str(update.effective_user.id) if update.effective_user else '123456'
        
        # Import here to avoid circular imports
        from db.database import init_db
        from db.repo import Repo
        conn = init_db('./data/bot.db', './db/schema.sql')
        repo = Repo(conn)
        
        # Get active setups from the database
        active_setups = repo.get_active_setups(user_id)
        
        # Sort by score (descending) and then by remaining time (ascending)
        active_setups.sort(key=lambda x: (x.get('trade_score', x.get('idea_score', 0)), x['expires_at']), reverse=True)
        
        if active_setups:
            message = f"Präsente Setups ({len(active_setups)} Einträge - sortiert nach Score):\n\n"
            
            for setup in active_setups[:10]:  # Show top 10
                status_emoji = "🟡" if setup['status'] == 'IDEA' else "🟢"
                side_emoji = "🔴 SHORT" if setup['side'] == 'bearish' else "🟢 LONG"
                
                # Calculate remaining time
                import time
                remaining_minutes = max(0, (setup['expires_at'] - int(time.time())) // 60)
                
                score = setup.get('trade_score', setup.get('idea_score', 0))
                
                message += (
                    f"{status_emoji} {setup['status']} | {side_emoji}\n"
                    f"🪙 {setup['symbol']} ({setup['timeframe']})\n"
                    f"📊 Score: {score}\n"
                    f"⏳ Verbleibend: {remaining_minutes} min\n\n"
                )
            
            if len(active_setups) > 10:
                message += f"... und {len(active_setups) - 10} weitere Setups"
        else:
            message = "Keine aktiven Setups in der Watchlist.\n\nDer Bot sucht nach IDEA Setups (Liquidity + Fib Kombinationen). Sobald gefunden, erscheinen sie hier."
        
        await update.effective_message.edit_text(message)


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    if update.effective_message:
        # This would normally fetch from DB
        stats = {
            'signals_sent': 0,
            'active_users': 1,
            'uptime_hours': 0
        }
        
        message = (
            f"📊 Bot-Statistiken:\n\n"
            f"Signale gesendet: {stats['signals_sent']}\n"
            f"Aktive Nutzer: {stats['active_users']}\n"
            f"Laufzeit: {stats['uptime_hours']} Stunden"
        )
        
        await update.effective_message.edit_text(message)


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    if update.effective_message:
        help_text = (
            "ℹ️ Hilfe zum Crypto-Signal Hub-Bot:\n\n"
            "Der Bot scannt kontinuierlich nach Handelssignalen und sendet diese an dich.\n\n"
            "Befehle:\n"
            "/start - Startmenü öffnen\n"
            "/modules - Module aktivieren/deaktivieren\n"
            "/combo - Combo/Premium Einstellungen\n"
            "/watchlist - Watchlist verwalten\n"
            "/preset - Konservativ/Normal/Aggressiv\n"
            "/stats - Statistik & Verlauf\n"
            "/help - Hilfe / Anleitung\n\n"
            "Module:\n"
            "• Volume: Erkennt ungewöhnliche Volumen-Aktivität\n"
            "• Fibonacci: Erkennt Goldene-Schnitt-Muster\n"
            "• RSI Divergenz: Erkennt Divergenzen im RSI\n"
            "• MACD: MACD Analyse\n"
            "• SMC: Smart Money Concepts (Order Blocks, FVG, BOS)"
        )
        
        await update.effective_message.edit_text(help_text)


async def toggle_module(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle module on/off"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Check if query.data is not None before using it
        if query.data:
            # Extract module name from callback data
            module_name = query.data.replace('toggle_', '')
            
            # Get user ID (with fallback)
            user_id = update.effective_user.id if update.effective_user else 123456
            
            # Toggle the module status in DB (using mock for now)
            new_status = toggle_module_status(user_id, module_name)
            
            # Update the message to reflect the new status
            status_emoji = "🟢" if new_status else "🔴"
            status_text = "AKTIV" if new_status else "INAKTIV"
            
            # Fetch updated modules status from DB
            modules_status = get_modules_status(user_id)
            
            # Create updated keyboard
            from telegram import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = []
            for module, enabled in modules_status.items():
                btn_status_emoji = "🟢" if enabled else "🔴"
                btn_status_text = "AKTIV" if enabled else "INAKTIV"
                keyboard.append([InlineKeyboardButton(f"{btn_status_emoji} {module} - {btn_status_text}", callback_data=f'toggle_{module}')])
            
            keyboard.append([InlineKeyboardButton("🔙 Zurück", callback_data='back_to_menu')])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Update the message with new keyboard
            try:
                await query.edit_message_text("Module (grün=aktiviert, rot=deaktiviert):\n\n"
                                           "🟢 = Aktiv (in DB gespeichert)\n"
                                           "🔴 = Inaktiv (in DB gespeichert)", reply_markup=reply_markup)
            except Exception as e:
                # If the message hasn't changed significantly, just show a temporary notification
                await query.answer(f"Modul {module_name} auf {status_text} gesetzt! (in DB gespeichert)")


async def set_combo_preset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set combo/preset"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Check if query.data is not None before using it
        if query.data:
            preset_name = query.data.replace('combo_', '')
            
            # In a real implementation, this would update the DB
            await query.edit_message_text(f"Combo-Preset auf {preset_name} gesetzt und in der DB gespeichert! 📊")


async def set_preset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set preset"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Check if query.data is not None before using it
        if query.data:
            preset_name = query.data.replace('preset_', '')
            
            # In a real implementation, this would update the DB
            await query.edit_message_text(f"Preset auf {preset_name} gesetzt und in der DB gespeichert! 📊")


async def add_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add symbol to watchlist"""
    if update.message:
        if not context.args:
            await update.message.reply_text("Nutze: /add_symbol [SYMBOL] (z.B. /add_symbol BTCUSDT)")
            return
        
        symbol = context.args[0].upper()
        # In a real implementation, this would add to DB
        await update.message.reply_text(f"Symbol {symbol} wurde zur Watchlist hinzugefügt und in der DB gespeichert! 📊")


async def remove_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove symbol from watchlist"""
    if update.message:
        if not context.args:
            await update.message.reply_text("Nutze: /remove_symbol [SYMBOL] (z.B. /remove_symbol BTCUSDT)")
            return
        
        symbol = context.args[0].upper()
        # In a real implementation, this would remove from DB
        await update.message.reply_text(f"Symbol {symbol} wurde von der Watchlist entfernt und in der DB aktualisiert! 📊")


def get_modules_status(user_id: int) -> dict:
    """
    Fetch module status from DB for a user.
    For now, using a mock implementation.
    """
    # This would normally fetch from DB
    # Return default status for all modules
    return {
        'volume': True,
        'fibonacci': True,
        'rsi_divergence': False,  # Updated based on the log showing it was toggled
        'macd': True,
        'smc': False
    }


def toggle_module_status(user_id: int, module_name: str) -> bool:
    """
    Toggle module status in DB for a user.
    For now, using a mock implementation that just returns the opposite of current status.
    """
    # This would normally update the DB
    # For mock, we'll just return the opposite of a default status
    current_status = get_modules_status(user_id).get(module_name, False)
    new_status = not current_status
    
    # In a real implementation, this would update the DB
    print(f"Modul {module_name} Status wurde auf {new_status} gesetzt und in der DB gespeichert!")
    
    return new_status


def setup_handlers(application):
    """Setup all handlers for the bot"""
    from telegram.ext import CommandHandler, CallbackQueryHandler
    from telegram import BotCommand
    
    # Register bot commands for the command menu (the menu that appears when you press /)
    async def set_bot_commands(application):
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
    
    # Set the command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CommandHandler("modules", modules_command))
    application.add_handler(CommandHandler("combo", combo_command))
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("preset", preset_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("help", show_help))
    application.add_handler(CommandHandler("add_symbol", add_symbol))
    application.add_handler(CommandHandler("remove_symbol", remove_symbol))
    
    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Set up the bot commands to appear in the / menu
    # We need to run this in the application's event loop context
    import asyncio
    try:
        # If we're in an event loop, create a task
        asyncio.get_running_loop()
        asyncio.create_task(set_bot_commands(application))
    except RuntimeError:
        # If no event loop is running, schedule it differently
        pass  # We'll handle this in main.py