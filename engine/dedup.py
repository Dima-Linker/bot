def make_dedup_key(tg_user_id: str, symbol: str, timeframe: str, signal_type: str, candle_ts: int, levels: dict = None, side: str = None) -> str:
    """
    Create fine-grained deduplication key to prevent false positives while allowing legitimate variations
    
    Key components:
    - symbol: trading pair
    - timeframe: 15m/1h/4h
    - signal_type: combo/idea/etc
    - candle_ts: timestamp for temporal uniqueness
    - side: long/short direction
    - levels: rounded zone/level information
    """
    
    # Base key components
    key_parts = [tg_user_id, symbol, timeframe, signal_type, str(candle_ts)]
    
    # Add side if available
    if side:
        key_parts.append(side)
    
    # Add rounded level information if available
    if levels:
        # Round levels to prevent too many similar keys
        if 'zone_low' in levels and 'zone_high' in levels:
            zone_mid = (levels['zone_low'] + levels['zone_high']) / 2
            key_parts.append(f"zone_{round(zone_mid, 2)}")
        elif 'fibo_level' in levels:
            key_parts.append(f"fibo_{round(levels['fibo_level'], 3)}")
        elif 'smc_level' in levels:
            key_parts.append(f"smc_{round(levels['smc_level'], 2)}")
        elif 'pump_pct' in levels:
            key_parts.append(f"pump_{round(levels['pump_pct'], 1)}")
    
    return ":".join(key_parts)

# Export function
__all__ = ['make_dedup_key']