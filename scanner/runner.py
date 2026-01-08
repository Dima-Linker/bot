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

def get_symbol_chunk(symbols, start_idx, chunk_size):
    """Get a chunk of symbols for round-robin scanning"""
    n = len(symbols)
    end_idx = start_idx + chunk_size
    if end_idx <= n:
        chunk = symbols[start_idx:end_idx]
        next_idx = end_idx % n
    else:
        chunk = symbols[start_idx:] + symbols[:end_idx - n]
        next_idx = end_idx - n
    return chunk, next_idx

def run_scan_for_user(repo, tg_user_id: str, bitget, telegram_send_fn, modules_registry: dict):
    start_time = time.time()  # Track scan start time for duration logging
    print(f"[SCAN] start {start_time}")
    
    # Initialize scan debugger
    from engine.scan_debugger import get_scan_debugger
    debugger = get_scan_debugger()
    debugger.reset_metrics()
    
    # Initialize Phase 1 selector
    from engine.phase1_selector import apply_phase1_selection
    
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
    
    # Set total symbols in debugger
    debugger.set_total_symbols(len(symbols))
    
    watchlist = set(settings.get('watchlist', []))
    if watchlist:
        symbols = [s for s in symbols if s in watchlist]

    combo_min_score = int(settings.get('combo_min_score', preset['combo_min_score']))
    cooldown_seconds = 30 if os.getenv('DEBUG_COOLDOWN') == '1' else int(preset['cooldown_hours']) * 3600

    # Scan metrics tracking
    expected_symbols = len(symbols)
    scanned_symbols = 0
    scan_errors = 0
    kline_calls = 0
    features_found_total = 0
    alerts_sent_total = 0
    
    # CHUNKING CONFIGURATION
    CHUNK_SIZE = 100  # Process 100 symbols per scan tick
    
    # Get current cursor position
    cursor = thread_repo.get_cursor(tg_user_id)
    print(f"[SCAN] Current cursor position: {cursor}")
    
    # Get symbol chunk for this scan
    chunk_symbols, next_cursor = get_symbol_chunk(symbols, cursor, CHUNK_SIZE)
    print(f"[SCAN] Processing chunk: {len(chunk_symbols)} symbols (index {cursor}-{(cursor + CHUNK_SIZE - 1) % len(symbols)})")
    print(f"[SCAN] First symbol: {chunk_symbols[0] if chunk_symbols else 'None'}")
    print(f"[SCAN] Last symbol: {chunk_symbols[-1] if chunk_symbols else 'None'}")
    
    # Update cursor for next scan
    thread_repo.set_cursor(tg_user_id, next_cursor)
    
    # COLLECT ALL DECISIONS FIRST (don't send yet)
    all_raw_decisions = []
    
    print(f"[SCAN-START] Expected to scan {len(chunk_symbols)} symbols in this chunk")
    print(f"[DEBUG] Starting symbol loop...")
    
    # SINGLE PASS - scan chunk symbols exactly once
    symbol_counter = 0
    for i, symbol in enumerate(chunk_symbols):
        symbol_counter += 1
        print(f"[DEBUG] Processing symbol {symbol_counter}/{len(chunk_symbols)}: {symbol}")
        
        # Progress logging every 25 symbols
        if i % 25 == 0 and i > 0:
            print(f"[SCAN-PROGRESS] {i}/{len(chunk_symbols)} chunk symbols processed. Last: {symbol}")
            print(f"[DEBUG] Current position in chunk: {i}/{len(chunk_symbols)}")
        
        try:
            # Fetch all timeframes for bias calculation
            all_candles = {}
            for tf in TIMEFRAMES:
                all_candles[tf] = bitget.get_klines(symbol, tf, limit=220)
                kline_calls += 1
                debugger.record_api_call()
            
            # Calculate bias for this symbol
            candles_4h = all_candles.get('4h', [])
            candles_1h = all_candles.get('1h', [])
            candles_15m = all_candles.get('15m', [])
            
            bias_result = bias_resolver.resolve_bias(symbol, candles_4h, candles_1h, candles_15m)
            
            # Record successful processing
            debugger.record_symbol_success(symbol)
            scanned_symbols += 1
            
        except Exception as e:
            print(f"[SCAN-ERROR] Failed to process {symbol}: {e}")
            debugger.record_symbol_failure(symbol, str(e)[:50])
            scan_errors += 1
            continue
            
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
                # Check for pure Fibonacci alerts first - LOOSEN criteria
                fib_features = [f for f in features if f.module == 'fibonacci']
                # Changed from >= 2 to >= 1 to catch more fib alerts
                if fib_features and len(fib_features) >= 1:
                    # Create pure Fibonacci alert
                    fib_alert = {
                        'symbol': symbol,
                        'timeframe': tf,
                        'type': 'FIBONACCI',  # Explicit FIBONACCI type
                        'message_type': 'FIB_ALERT',  # Dedicated alert type
                        'score_total': sum(f.score for f in fib_features[:2]),  # Sum top 2 fib scores
                        'side': fib_features[0].direction,
                        'reasons': [f.reasons[0] if f.reasons else f"Golden Zone touch at {f.levels.get('actual_level', 'N/A')}" for f in fib_features[:2]],
                        'levels': {k: v for f in fib_features for k, v in f.levels.items()},
                        'setup_id': f"fib_{symbol}_{tf}_{int(time.time())}"
                    }
                    print(f"[FIB-ALERT] {symbol} {tf} score={fib_alert['score_total']}")
                    all_raw_decisions.append(fib_alert)
                    continue  # Skip regular decision logic for pure fib alerts
                
                # Use the new state-based decision engine with IDEA vs TRADE for non-Fib setups
                decision = decide_signal_with_states(features, combo_min_score, thread_repo, tg_user_id, settings.get('preset', 'normal'))
                if decision:
                    print(f"decision {decision['type'] if decision else None} {decision.get('score_total') if decision else None}")
                    
                    # COLLECT ALL DECISIONS - don't send yet
                    all_raw_decisions.append(decision)
                    
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
    
    # DEBUG: Show completion status
    print(f"[DEBUG] Symbol loop completed!")
    print(f"[DEBUG] Total symbols processed: {symbol_counter}")
    print(f"[DEBUG] Expected symbols: {expected_symbols}")
    print(f"[DEBUG] Raw decisions collected: {len(all_raw_decisions)}")
    
    # CATEGORIZATION DEBUG - prove the separation rules
    decisions_combo = len([d for d in all_raw_decisions if d.get('type') == 'COMBO'])
    decisions_idea = len([d for d in all_raw_decisions if d.get('type') == 'IDEA'])
    alerts_fib = len([d for d in all_raw_decisions if d.get('message_type') == 'FIB_ALERT'])
    alerts_liq = len([d for d in all_raw_decisions if d.get('type') == 'LIQUIDITY'])
    alerts_pump = len([d for d in all_raw_decisions if d.get('type') == 'PUMP'])
    
    print(f"[DEBUG-COUNT] decisions_found: combo={decisions_combo} idea={decisions_idea}")
    print(f"[DEBUG-COUNT] alerts_found: fib_alert={alerts_fib} liq_alert={alerts_liq} pump_alert={alerts_pump}")
    
    # TEMPORARY: Bypass selection to debug - send ALL raw decisions
    print(f"[DEBUG] BYPASSING SELECTION - sending ALL {len(all_raw_decisions)} raw decisions")
    selected_decisions = all_raw_decisions[:]  # Make a copy
    
    # Alternative: Very loose selection (comment out if above works)
    # selected_decisions = apply_phase1_selection(all_raw_decisions, thread_repo, tg_user_id)
    
    print(f"[SELECTION] Selected {len(selected_decisions)} signals for sending")
    
    # PROOF LOGS - show what gets selected per category
    selected_combo = len([d for d in selected_decisions if d.get('type') == 'COMBO'])
    selected_idea = len([d for d in selected_decisions if d.get('type') == 'IDEA'])
    selected_fib = len([d for d in selected_decisions if d.get('message_type') == 'FIB_ALERT'])
    
    print(f"[DEBUG-SELECTED] selected: combo={selected_combo} idea={selected_idea} fib_alert={selected_fib}")
    
    # SEND ONLY SELECTED DECISIONS
    print(f"[DEBUG] Starting to send {len(selected_decisions)} selected decisions...")
    for i, decision in enumerate(selected_decisions):
        print(f"[DEBUG] Sending decision {i+1}/{len(selected_decisions)}: {decision['symbol']} {decision['timeframe']}")
        
        symbol = decision['symbol']
        tf = decision['timeframe']
        
        # PROOF LOG - critical for verification
        signal_kind = decision.get('type', 'UNKNOWN')
        message_type = decision.get('message_type', 'UNKNOWN')
        print(f"[SEND-PROOF] kind={signal_kind} message_type={message_type} symbol={symbol} tf={tf}")
        
        # Build and send message (existing logic)
        message = build_message(symbol, tf, decision)
        print(f"send_to {tg_user_id} msglen {len(message)}")
        
        # Prepare chart overlays and indicators from features
        overlays = {}
        indicators = {}
        
        # Extract horizontal levels (zones) from features
        hlevels = []
        # Note: We don't have access to original features here, so we use decision levels
        levels = decision.get('levels', {})
        if 'zone_low' in levels and 'zone_high' in levels:
            hlevels.append(levels['zone_low'])
            hlevels.append(levels['zone_high'])
        elif 'fibo_618' in levels:
            hlevels.append(levels['fibo_618'])
        elif 'fibo_786' in levels:
            hlevels.append(levels['fibo_786'])
        
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
            levels = decision.get('levels', {})
            if 'tp_levels' in levels:
                annotation_data['tp_levels'] = levels['tp_levels']
            elif 'take_profit_levels' in levels:
                annotation_data['tp_levels'] = levels['take_profit_levels']
            if 'stop_loss_level' in levels:
                annotation_data['sl_level'] = levels['stop_loss_level']
            elif 'stop_level' in levels:
                annotation_data['sl_level'] = levels['stop_level']
        
        # Render chart (simplified - would need original candles/features)
        chart_path = None  # Placeholder - would need to reconstruct
        
        # Handle cooldown differently based on message type
        if decision.get('message_type') == 'FIB_ALERT':
            # FIB alerts get their own cooldown logic
            cooldown_key = f"fib_alert:{symbol}:{tf}"
            current_cooldown = 90 * 60  # 90 minutes base cooldown
        elif decision.get('message_type') == 'WATCHLIST':
            cooldown_key = f"idea:{symbol}:{tf}:{decision.get('setup_id', '')}"
            current_cooldown = 30 * 60  # 30 minutes for IDEA
        elif decision.get('message_type') == 'TRADE_FREIGABE':
            cooldown_key = f"trade:{symbol}:{tf}:{decision.get('setup_id', '')}"
            current_cooldown = 60 * 60  # 60 minutes for TRADE
        else:
            cooldown_key = f"{decision['type']}:{symbol}:{tf}"
            current_cooldown = cooldown_seconds
        
        # Add to cooldown and dedup (would need to reconstruct original logic)
        # thread_repo.set_cooldown(tg_user_id, cooldown_key, current_cooldown)
        
        # Send via Telegram with chart
        try:
            # Pass signal data for topic routing
            signal_data = {
                'module': decision.get('module_used', ''),
                'score': decision.get('score_total', 0),
                'type': decision.get('type', ''),
                'message_type': decision.get('message_type', ''),
                'side': decision.get('side', ''),
                'setup_id': decision.get('setup_id', '')
            }
            telegram_send_fn(
                chat_id=tg_user_id, 
                text=message, 
                chart_path=chart_path,
                signal_data=signal_data
            )
            debugger.record_alert_sent(decision.get('type', 'unknown'))
        except Exception as e:
            print(f"Telegram send error: {e}")
            continue
    
    # FINAL MONITORING LOGS - EXACTLY AS REQUESTED
    print("[DEBUG] Preparing final monitoring logs...")
    total_candidates = len(all_raw_decisions)
    unique_symbols_candidates = len(set(d['symbol'] for d in all_raw_decisions))
    selected_count = len(selected_decisions)
    unique_symbols_selected = len(set(d['symbol'] for d in selected_decisions))
    
    # Count topics in selected decisions
    topic_counts = {}
    for decision in selected_decisions:
        topic = decision.get('type', 'UNKNOWN')
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    print("=== FINAL SCAN RESULTS ===")
    print(f"SCAN DONE: candidates={total_candidates}, unique_symbols={unique_symbols_candidates}")
    print(f"SELECTED: total={selected_count}, unique_symbols={unique_symbols_selected}")
    print(f"TOPICS: {' '.join([f'{k}={v}' for k, v in topic_counts.items()])}")
    print("==========================")
    
    # Scan completion summary
    print(f"[SCAN-END] expected={len(chunk_symbols)} scanned={scanned_symbols} errors={scan_errors}")
    print(debugger.generate_simple_summary())
    
    # CLEAN EXIT - no looping, single pass only
    print("[SCAN] Single scan cycle completed. Exiting.")
    print("[DEBUG] Function returning...")
    return
