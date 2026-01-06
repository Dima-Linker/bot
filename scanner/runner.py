import time
import os
from engine.decision import decide_signal, decide_signal_with_states
from engine.dedup import make_dedup_key
from engine.message_builder import build_message
from engine.presets import PRESETS
from engine.bias_resolver import bias_resolver
import pandas as pd
from charts.renderer import render_chart_png

TIMEFRAMES = ['15m', '1h', '4h']

def reduce_features(features, max_per_module=3):
    by_mod = {}
    for f in features:
        by_mod.setdefault(f.module, []).append(f)

    reduced = []
    for mod, arr in by_mod.items():
        arr_sorted = sorted(arr, key=lambda x: x.score, reverse=True)
        reduced.extend(arr_sorted[:max_per_module])
    return reduced

def run_scan_for_user(repo, tg_user_id: str, bitget, telegram_send_fn, modules_registry: dict):
    print(f"[SCAN] start {time.time()}")
    
    # Create a new database connection for this thread
    from db.database import init_db
    from db.repo import Repo
    conn = init_db('./data/bot.db', './db/schema.sql')
    thread_repo = Repo(conn)
    
    # Get settings using the thread-specific repo
    settings = thread_repo.get_settings(tg_user_id)
    from engine.presets import PRESETS
    preset = PRESETS.get(settings.get('preset', 'normal'), PRESETS['normal'])

    symbols = bitget.list_usdt_perp_symbols()
    print(f"[SCAN] symbols {len(symbols)}")
    
    watchlist = set(settings.get('watchlist', []))
    if watchlist:
        symbols = [s for s in symbols if s in watchlist]

    combo_min_score = int(settings.get('combo_min_score', preset['combo_min_score']))
    cooldown_seconds = 30 if os.getenv('DEBUG_COOLDOWN') == '1' else int(preset['cooldown_hours']) * 3600

    for symbol in symbols[:5]:  # Limit to first 5 symbols for testing
        # Fetch all timeframes for bias calculation
        all_candles = {}
        for tf in TIMEFRAMES:
            all_candles[tf] = bitget.get_klines(symbol, tf, limit=220)
        
        # Calculate bias for this symbol
        candles_4h = all_candles.get('4h', [])
        candles_1h = all_candles.get('1h', [])
        candles_15m = all_candles.get('15m', [])
        
        bias_result = bias_resolver.resolve_bias(symbol, candles_4h, candles_1h, candles_15m)
        
        for tf in TIMEFRAMES:
            print(f"[SCAN] fetching {symbol} {tf}")
            candles = all_candles[tf]
            if len(candles) < 80:
                continue

            # Convert candles to DataFrame for the new modules
            df = pd.DataFrame(candles)
            df = df[['ts', 'open', 'high', 'low', 'close', 'volume']].copy()
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            # Log candle info
            if len(candles) > 1:
                print(f"{symbol} {tf} {len(candles)} {candles[-2]['ts']} {candles[-2]['volume']}")
            
            features = []
            for module_name, module in modules_registry.items():
                if not settings.get(f"module_{module_name}", True):
                    continue  # Skip disabled modules
                
                # Use the new analyze function with DataFrame
                try:
                    # For SMC module, pass the target direction to filter FVG appropriately
                    if module_name == 'smc':
                        # Determine target direction based on bias for FVG filtering
                        bias_data = bias_resolver.bias_cache.get(symbol, {})
                        htf_bias = bias_data.get('4h', None)
                        
                        # If bias is BEAR and we're looking for short signals, only include bearish FVG
                        # If bias is BULL and we're looking for long signals, only include bullish FVG
                        target_direction = None
                        if htf_bias and htf_bias.value == 'BEAR':
                            target_direction = 'short'
                        elif htf_bias and htf_bias.value == 'BULL':
                            target_direction = 'long'
                        
                        module_results = module.analyze(df, target_direction=target_direction)
                    else:
                        module_results = module.analyze(df)
                    print(f"feature {module_name} => {len(module_results) if module_results else 0}")
                    for result in module_results:
                        # Update the result with actual values
                        result.symbol = symbol
                        result.timeframe = tf
                        result.candle_ts = candles[-2]['ts']  # Use stable candle
                        features.append(result)
                except Exception as e:
                    print(f"Error in {module_name} module: {e}")
                    continue

            # Apply feature reduction: Top-K per module with specific limits
            max_per_module_map = {
                'volume': 1,
                'rsi_divergence': 1,
                'macd': 2,
                'fibonacci': 2,
                'smc': 2
            }
            
            # Process each module separately with its specific limit
            reduced_features = []
            by_mod = {}
            for f in features:
                by_mod.setdefault(f.module, []).append(f)
            
            for mod, arr in by_mod.items():
                max_per_mod = max_per_module_map.get(mod, 1)
                arr_sorted = sorted(arr, key=lambda x: x.score, reverse=True)
                reduced_features.extend(arr_sorted[:max_per_mod])
            
            features = reduced_features
            
            print(f"features_count {len(features)}")
            
            # Decision making
            if features:
                # Use the new state-based decision engine with IDEA vs TRADE
                decision = decide_signal_with_states(features, combo_min_score, thread_repo, tg_user_id, settings.get('preset', 'normal'))
                if decision:
                    print(f"decision {decision['type'] if decision else None} {decision.get('score_total') if decision else None}")
                    
                    # Validate setup consistency with higher timeframe bias
                    setup_direction = decision.get('side', 'both')
                    is_consistent, validation_reason = bias_resolver.validate_setup_consistency(symbol, setup_direction, tf)
                    
                    if not is_consistent:
                        # For countertrend setups, downgrade to IDEA or skip based on settings
                        if decision.get('message_type') == 'TRADE_FREIGABE':
                            print(f"DOWNGRADE: {validation_reason} -> converting to IDEA")
                            decision['message_type'] = 'WATCHLIST'
                            decision['type'] = 'IDEA'
                            decision['reasons'].append(f"⚠️ Countertrend: {validation_reason}")
                        else:
                            print(f"SKIPPED: {validation_reason}")
                            continue
                    
                    # Handle cooldown differently based on message type
                    if decision.get('message_type') == 'WATCHLIST':
                        # IDEA messages have shorter cooldown
                        cooldown_key = f"idea:{symbol}:{tf}:{decision.get('setup_id', '')}"
                        current_cooldown = 30 * 60  # 30 minutes for IDEA
                    elif decision.get('message_type') == 'TRADE_FREIGABE':
                        # TRADE messages have longer cooldown
                        cooldown_key = f"trade:{symbol}:{tf}:{decision.get('setup_id', '')}"
                        current_cooldown = 60 * 60  # 60 minutes for TRADE
                    else:
                        # Legacy combo messages
                        cooldown_key = f"{decision['type']}:{symbol}:{tf}"
                        current_cooldown = cooldown_seconds
                    
                    if thread_repo.is_in_cooldown(tg_user_id, cooldown_key):
                        print("SKIP cooldown")
                        continue

                    # Check deduplication
                    dedup_key = make_dedup_key(
                        tg_user_id=tg_user_id,
                        symbol=symbol,
                        timeframe=tf,
                        signal_type=decision['type'],
                        candle_ts=candles[-2]['ts'],
                        levels=decision.get('levels', {})
                    )
                    if thread_repo.has_dedup_key(dedup_key):
                        print("SKIP dedup")
                        continue

                    # Build and send message
                    message = build_message(symbol, tf, decision)
                    print(f"send_to {tg_user_id} msglen {len(message)}")
                    
                    # Prepare chart overlays and indicators from features
                    overlays = {}
                    indicators = {}
                    
                    # Extract horizontal levels (zones) from features
                    hlevels = []
                    for feature in features:
                        if feature.levels:
                            # Add zone boundaries for SMC (Order Blocks, FVGs)
                            if 'zone_low' in feature.levels and 'zone_high' in feature.levels:
                                hlevels.append(feature.levels['zone_low'])
                                hlevels.append(feature.levels['zone_high'])
                            # Add Fibonacci levels
                            elif 'fibo_618' in feature.levels:
                                hlevels.append(feature.levels['fibo_618'])
                            elif 'fibo_786' in feature.levels:
                                hlevels.append(feature.levels['fibo_786'])
                            # Add other level types if present
                            for key, value in feature.levels.items():
                                if 'level' in key.lower() or '_price' in key.lower():
                                    hlevels.append(value)
                    
                    if hlevels:
                        overlays['hlevels'] = list(set(hlevels))  # Remove duplicates
                    
                    # Prepare annotation data for the chart
                    annotation_data = {
                        'direction': decision.get('side', 'both'),
                        'score': decision.get('score_total', 0) / 15 if decision.get('score_total') else 0,  # Scale to 10
                        'reasons': decision.get('reasons', [])[:3]  # Limit to 3 reasons
                    }
                    
                    # Add TP/SL levels if available in decision data
                    if decision.get('message_type') == 'TRADE_FREIGABE':
                        # Extract TP and SL levels from decision data if available
                        levels = decision.get('levels', {})
                        if 'tp_levels' in levels:
                            annotation_data['tp_levels'] = levels['tp_levels']
                        elif 'take_profit_levels' in levels:
                            annotation_data['tp_levels'] = levels['take_profit_levels']
                        if 'stop_loss_level' in levels:
                            annotation_data['sl_level'] = levels['stop_loss_level']
                        elif 'stop_level' in levels:
                            annotation_data['sl_level'] = levels['stop_level']
                    
                    # Render chart with overlays and annotations
                    chart_path = render_chart_png(symbol, tf, candles, overlays=overlays, indicators=indicators, annotation=annotation_data)
                    
                    # --- make JSON safe payload ---
                    serial_features = [f.to_dict() for f in features]

                    serial_decision = dict(decision)
                    # Wichtig: decision enthält oft FeatureResult-Objekte
                    if "features" in serial_decision:
                        serial_decision["features"] = [f.to_dict() for f in serial_decision["features"]]

                    payload = {
                        "decision": serial_decision,
                        "features": serial_features,
                    }
                    
                    # Add to cooldown and dedup
                    thread_repo.set_cooldown(tg_user_id, cooldown_key, current_cooldown)
                    thread_repo.save_sent_signal(
                        tg_user_id=tg_user_id,
                        dedup_key=dedup_key,
                        symbol=symbol,
                        timeframe=tf,
                        signal_type=decision['type'],
                        candle_ts=candles[-2]['ts'],
                        score_total=decision.get('score_total'),
                        payload=payload,
                    )
                    
                    # Send via Telegram with chart
                    try:
                        telegram_send_fn(chat_id=tg_user_id, text=message, chart_path=chart_path)
                    except Exception as e:
                        print(f"Telegram send error: {e}")
                        continue