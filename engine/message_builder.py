def build_message(symbol: str, timeframe: str, decision: dict) -> str:
    """Build formatted message for Telegram based on decision data"""
    signal_type = decision['type']
    score_total = decision.get('score_total')
    reasons = decision.get('reasons', [])
    side = decision.get('side', '')
    
    # Module mapping for display
    module_icons = {
        'fibonacci': '[FIB] 📐',
        'volume': '[VOL] 📊',
        'macd': '[MACD] 🔵',
        'rsi_divergence': '[RSI] 📈',
        'smc': '[SMC] 🏦',
        'pump': '[PUMP] 🔥'
    }
    
    # Build message header based on signal type
    if signal_type == 'combo':
        header = '[COMBO] 🧠 High-Quality Setup'
    elif signal_type == 'idea':
        header = '[IDEA] 🟡 Watchlist Setup'
    else:
        header = f'[{signal_type.upper()}] Setup'
    
    # Build reasons section
    reasons_text = '\n'.join([f'• {reason}' for reason in reasons[:3]]) if reasons else 'No specific reasons'
    
    # Build score display
    score_display = f'Score: {score_total}/400' if score_total else 'Score: N/A'
    
    # Build side indicator
    side_indicator = f'Direction: {side.upper()}' if side else ''
    
    # Combine all parts
    message_parts = [
        header,
        f'🪙 {symbol} | TF: {timeframe}',
        score_display,
        side_indicator,
        '',
        'Reasons:',
        reasons_text
    ]
    
    # Filter out empty parts
    message_parts = [part for part in message_parts if part]
    
    return '\n'.join(message_parts)

def auto_classify_signal(message_text: str) -> str:
    """Automatically classify signal type for topic routing"""
    text_lower = message_text.lower()
    
    # Priority classification based on content
    if 'fibonacci' in text_lower or 'fib' in text_lower or 'golden ratio' in text_lower:
        return 'FIBONACCI'
    elif 'pump' in text_lower or 'momentum' in text_lower or 'volume spike' in text_lower:
        return 'PUMP'
    elif 'liquidity' in text_lower or 'smc' in text_lower or 'stop hunt' in text_lower:
        return 'LIQUIDITY'
    elif 'combo' in text_lower or 'high-quality' in text_lower:
        return 'COMBO'
    elif 'idea' in text_lower or 'watchlist' in text_lower:
        return 'IDEA'
    else:
        # Default classification based on score context
        if '/400' in message_text:
            return 'COMBO'  # High score = COMBO
        else:
            return 'IDEA'   # Lower score = IDEA


# Update exports
__all__ = [
    'build_message',
    'build_fib_alert_message', 
    'build_smc_alert_message',
    'build_pump_alert_message',
    'auto_classify_signal'  # NEW
]