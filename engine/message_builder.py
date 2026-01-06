from engine.types import FeatureResult
from engine.bias_resolver import MarketBias
from typing import Optional

def _dir_label(direction: str) -> tuple[str, str]:
    d = (direction or "both").lower()
    if d == "long":
        return "LONG", "🟢"
    if d == "short":
        return "SHORT", "🔴"
    return "LONG/SHORT", "🟡"

MODULE_TITLES = {
    "volume": ("[VOLUME] 🔥", "Volumen-Impuls"),
    "fibo": ("[FIBO] 🧲", "Fibonacci-Zone"),
    "rsi_div": ("[DIVERGENZ] 🟢", "RSI-Divergenz"),
    "macd": ("[MACD] 🔵", "MACD-Signal"),
    "smc": ("[SMC] 🏦", "Smart-Money-Zone"),
}

def build_message_de(symbol: str, timeframe: str, decision: dict, htf_bias: Optional[MarketBias] = None) -> str:
    signal_type = decision["type"]
    score_total = decision.get("score_total")

    # Features (können FeatureResult-Objekte sein oder dicts – je nachdem wie du speicherst)
    features = decision.get("features", [])
    if features and isinstance(features[0], dict):
        # wenn dicts: minimal rausziehen
        direction = features[0].get("direction", "both")
        reasons = []
        for f in features:
            reasons.extend(f.get("reasons", []))
    else:
        direction = features[0].direction if features else "both"
        reasons = []
        for f in features:
            reasons.extend(f.reasons)

    dir_label, dir_emoji = _dir_label(direction)

    # Add bias context if available
    bias_context = f" | 4h Bias: {htf_bias.value if htf_bias else 'N/A'}" if htf_bias else ""

    # Determine if this is an IDEA or TRADE based on score and context
    is_idea = score_total < 250 if score_total is not None else True
    
    if signal_type == "combo":
        if is_idea:
            header = "[IDEA] 🟡 Watchlist Setup"
        else:
            header = "[COMBO] 🧠 High-Quality Setup"
        subtitle = "Mehrere Bestätigungen gleichzeitig"
    else:
        mod = signal_type.split(":", 1)[1]
        tag, subtitle = MODULE_TITLES.get(mod, ("[SIGNAL]", "Setup"))
        is_idea = score_total < 250 if score_total is not None else True
        if is_idea:
            header = "[IDEA] 🟡 Watchlist Setup"
        else:
            header = f"{tag} Starkes Signal"

    # Gründe (max 6)
    why = "\n".join([f"• {r}" for r in reasons[:6]]) if reasons else "• Mehrere Bedingungen erfüllt"

    # Handlungsempfehlung (simple, robust) basierend auf IDEA/TRADE Status
    is_idea = score_total < 250 if score_total is not None else True
    if is_idea:
        action = (
            "🔍 Setup beobachten: Bestätigung abwarten (Break & Close / Retest)\n"
            "⏰ Entry: erst nach Bestätigung handeln\n"
            "⚠️ Risiko: Nur bei bestätigtem Signal einsteigen"
        )
    else:
        action = (
            "✅ Entry: Bestätigung abwarten (Break & Close / Retest)\n"
            "🛑 Stopp: unter/über letztes Swing-Level\n"
            "🎯 Take-Profit: Teilgewinn bei 1:1, Rest laufen lassen (R:R ≥ 1:2)"
        )

    score_line = f"📊 Score: {score_total}/400" if signal_type == "combo" else f"📊 Score: {score_total}/100"
    if score_total is None:
        score_line = ""

    return (
        f"{header}\n"
        f"🪙 {symbol} (USDT Perp)\n"
        f"🕒 TF: {timeframe}{bias_context}\n"
        f"🎯 Richtung: {dir_emoji} {dir_label}\n"
        f"{score_line}\n\n"
        f"Warum?\n{why}\n\n"
        f"Handlung:\n{action}\n\n"
        f"⚠️ Hinweis: Keine Finanzberatung. Risiko-Management beachten."
    )

def build_watchlist_message(symbol: str, timeframe: str, setup_result: dict, htf_bias: Optional[MarketBias] = None) -> str:
    """Build WATCHLIST message for IDEA setups"""
    idea_score = setup_result.get('score_total', 0)
    reasons = setup_result.get('reasons', [])
    levels = setup_result.get('levels', {})
    side = setup_result.get('side', 'both')
    
    dir_label, dir_emoji = _dir_label(side)
    
    # Add bias context if available
    bias_context = f" | 4h Bias: {htf_bias.value if htf_bias else 'N/A'}" if htf_bias else ""
    
    # Convert score to 10-point scale
    score_scaled = round(idea_score / 15, 1) if idea_score > 0 else 0
    
    # Build reasons section
    why_lines = []
    for reason in reasons[:4]:  # Limit to 4 main reasons
        # Format reasons more concisely
        reason_text = reason
        if 'Liquidity' in reason:
            reason_text = reason_text.replace('Liquidity', '⚡ Liquidity')
        elif 'Fibonacci' in reason:
            reason_text = f"⚡ Fibonacci {reason_text.split('Fibonacci')[1].strip()}"
        elif 'Order Block' in reason:
            reason_text = f"+ Bullish Order Block"
        elif 'Divergenz' in reason:
            reason_text = f"+ RSI Divergenz"
        why_lines.append(reason_text)
    
    # Add level information
    if levels:
        if 'sweep_level' in levels and 'fib_hit_price' in levels:
            # Calculate fib ratio for display
            fib_ratio = levels.get('fib_hit_ratio', 0)
            why_lines.insert(0, f"⚡ Liquidity Grab + Golden Zone ({fib_ratio:.3f} Fib)")
        if 'sweep_level' in levels:
            why_lines.append(f"• Liquidity Sweep bei {levels['sweep_level']}")
        if 'fib_zone_low' in levels and 'fib_zone_high' in levels:
            why_lines.append(f"• Fibonacci Zone {levels['fib_zone_low']}-{levels['fib_zone_high']}")
    
    why_section = "\n".join(why_lines) if why_lines else "⚡ Starke Konfluencen erkannt"
    
    # Calculate remaining time
    import time
    expires_at = setup_result.get('expires_at', int(time.time()) + 7200)  # Default 2 hours
    remaining_minutes = max(0, (expires_at - int(time.time())) // 60)
    
    return (
        f"🔔 NEUE SETUP-IDEA ERKANNT\n\n"
        f"₿ {symbol} | {timeframe}{bias_context} | {dir_emoji} {dir_label}\n\n"
        f"Score: {score_scaled}/10 ⭐⭐⭐⭐⭐\n\n"
        f"{why_section}\n\n"
        f"⏳ Gültig bis: {remaining_minutes} min verbleibend\n\n"
        f"🔍 Wir warten nun auf Bestätigung (CHoCH oder Break & Close).\n"
        f"Sobald TRADE freigegeben, kommt sofort Update!\n\n"
        f"Risiko: Nur bei bestätigtem TRADE einsteigen."
    )

def build_trade_message(symbol: str, timeframe: str, setup_result: dict, htf_bias: Optional[MarketBias] = None) -> str:
    """Build TRADE FREIGABE message for confirmed trades"""
    trade_score = setup_result.get('score_total', 0)
    reasons = setup_result.get('reasons', [])
    levels = setup_result.get('levels', {})
    side = setup_result.get('side', 'both')
    
    dir_label, dir_emoji = _dir_label(side)
    
    # Add bias context if available
    bias_context = f" | 4h Bias: {htf_bias.value if htf_bias else 'N/A'}" if htf_bias else ""
    
    # Build confirmation reasons
    confirm_lines = []
    for reason in reasons[:3]:  # Limit to 3 main confirmations
        confirm_lines.append(f"{reason}")
    
    confirmation_section = " | ".join(confirm_lines) if confirm_lines else "SETUP BESTÄTIGT: Starke Bestätigung erhalten"
    
    # Format confirmation as a single line
    confirmation_text = f"SETUP BESTÄTIGT: {confirmation_section}" if confirm_lines else "SETUP BESTÄTIGT: Starke Bestätigung erhalten"
    
    # Add stop loss and take profit levels
    sl_level = "unter letztem Swing Low" if side == 'long' else "über letztem Swing High"
    tp1_level = ""  # Will be calculated based on levels
    tp2_level = ""  # Will be calculated based on levels
    
    # Add specific levels if available
    entry_zone = ""
    if levels:
        if 'break_level' in levels:
            sl_level = f"unter {levels['break_level']}" if side == 'long' else f"über {levels['break_level']}"
        if 'choch_level' in levels:
            tp1_level = str(levels['choch_level'])
        if 'zone_low' in levels and 'zone_high' in levels:
            entry_zone = f"{levels['zone_low']} – {levels['zone_high']}"
    
    # Calculate risk/reward ratio
    risk_reward = "1:2"  # Default
    if 'zone_low' in levels and 'zone_high' in levels and sl_level:
        # Simple calculation based on entry and stop levels
        try:
            if side == 'long' and 'break_level' in levels:
                entry = (float(levels['zone_low']) + float(levels['zone_high'])) / 2
                stop = float(str(levels['break_level']).split()[-1])  # Extract number from string
                if 'unter' in sl_level:
                    risk = entry - stop
                    if tp1_level:
                        reward = float(tp1_level) - entry
                        if risk > 0:
                            risk_reward = f"1:{reward/risk:.1f}"
        except:
            risk_reward = "1:2"  # Fallback
    
    # Calculate remaining time
    import time
    expires_at = setup_result.get('expires_at', int(time.time()) + 7200)  # Default 2 hours
    remaining_minutes = max(0, (expires_at - int(time.time())) // 60)
    
    return (
        f"🚀 TRADE FREIGABE – JETZT EINSTEIGEN!\n\n"
        f"₿ {symbol} | {timeframe}{bias_context} | {dir_emoji} {dir_label}\n\n"
        f"⚡ {confirmation_text}\n\n"
    ) + (
        f"Entry-Zone: {entry_zone}\n" if entry_zone else ""
    ) + (
        f"TP1: {tp1_level} | TP2: Open\n" if tp1_level else "TP1: 1:1 | TP2: 1:2\n"
    ) + (
        f"SL: {sl_level}\n\n"
        f"RR: 1:{risk_reward} (konservativ)\n\n"
        f"⏰ Gültig bis: {remaining_minutes} min\n\n"
        f"Aggressiver Einstieg möglich – starkes Momentum!\n"
        f"Immer eigenes Risikomanagement beachten."
    )

def build_message(symbol: str, timeframe: str, decision: dict) -> str:
    """Build appropriate message based on decision type"""
    message_type = decision.get('message_type', 'COMBO')
    
    # Get bias information if available
    from engine.bias_resolver import bias_resolver
    bias_data = bias_resolver.bias_cache.get(symbol, {})
    htf_bias = bias_data.get('4h', None)
    
    if message_type == 'WATCHLIST':
        return build_watchlist_message(symbol, timeframe, decision, htf_bias)
    elif message_type == 'TRADE_FREIGABE':
        return build_trade_message(symbol, timeframe, decision, htf_bias)
    else:
        # Fallback to original combo message
        return build_message_de(symbol, timeframe, decision, htf_bias)