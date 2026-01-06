"""
Fibonacci Module for the Crypto-Signal Hub-Bot
Detects Golden Ratio (Golden Section) signals with consistent labeling
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class FibonacciSettings:
    """Settings for Fibonacci analysis"""
    enabled: bool = True
    golden_ratio_levels: Optional[List[float]] = None  # [0.618, 0.786, 1.618, etc.]
    min_price_deviation: float = 0.005  # 0.5% minimum deviation to qualify
    rsi_confirmation: bool = True  # Require RSI confirmation
    volume_confirmation: bool = True  # Require volume confirmation
    
    def __post_init__(self):
        if self.golden_ratio_levels is None:
            self.golden_ratio_levels = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618]


def calculate_rsi(close_prices: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = close_prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return pd.Series(rsi)  # Ensure return type is Series


def find_recent_swings(df: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
    """Find recent confirmed swing high and low using simple pivot logic"""
    if len(df) < 10:
        return None, None
    
    highs = df['high'].values
    lows = df['low'].values
    
    # Simple pivot detection: point is higher/lower than neighbors
    swing_high = None
    swing_low = None
    
    # Look for recent swings in last 30 candles
    for i in range(len(df)-30, len(df)-2):
        if i < 2 or i >= len(highs) - 2:
            continue
            
        # Check for swing high
        if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
            highs[i] > highs[i+1] and highs[i] > highs[i+2]):
            if swing_high is None or highs[i] > swing_high:
                swing_high = float(highs[i])
        
        # Check for swing low
        if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
            lows[i] < lows[i+1] and lows[i] < lows[i+2]):
            if swing_low is None or lows[i] < swing_low:
                swing_low = float(lows[i])
    
    return swing_high, swing_low


def fibonacci_analysis(df: pd.DataFrame, settings: FibonacciSettings) -> List[FeatureResult]:
    """
    Analyze price action around Fibonacci levels with consistent Golden Zone labeling
    """
    if len(df) < 50 or settings.enabled is False:
        return []
    
    results = []
    
    # Calculate Fibonacci levels based on recent confirmed swing points
    swing_high, swing_low = find_recent_swings(df)
    
    if swing_high is None or swing_low is None or swing_high <= swing_low:
        return []
    
    price_range = swing_high - swing_low
    current_price = df['close'].iloc[-1]
    
    # Determine swing direction (UP or DOWN)
    swing_direction = "UP" if df['close'].iloc[-10] < df['close'].iloc[-1] else "DOWN"
    
    # Check golden zone levels specifically (0.618-0.786)
    golden_levels = [0.618, 0.786]
    for level in golden_levels:
        fib_level = swing_low + (price_range * level)
        
        # Check if price is near this Fibonacci level
        deviation = abs(current_price - fib_level) / current_price
        
        if deviation <= settings.min_price_deviation:
            # Determine zone type based on swing direction and level
            zone_type = "pullback" if swing_direction == "UP" and level >= 0.618 else \
                       "retrace" if swing_direction == "DOWN" and level >= 0.618 else "neutral"
            
            # Direction based on zone type
            direction: Direction = "long" if zone_type == "pullback" else "short" if zone_type == "retrace" else "both"
            
            # Additional confirmations
            rsi_confirmed = True
            volume_confirmed = True
            
            # Zone boundaries for pullback/retrace
            zone_width = price_range * 0.05  # 5% zone width
            zone_low = fib_level - zone_width/2
            zone_high = fib_level + zone_width/2
            
            if settings.rsi_confirmation and len(df) > 14:
                # Calculate RSI
                close_series = pd.Series(df['close'])
                rsi = calculate_rsi(close_series, 14)
                current_rsi = rsi.iloc[-1] if hasattr(rsi, 'iloc') else rsi[-1] if isinstance(rsi, (list, np.ndarray)) else rsi
                
                # RSI confirmation based on direction
                if zone_type == "pullback":
                    rsi_confirmed = current_rsi < 70  # Not overbought for long entries
                elif zone_type == "retrace":
                    rsi_confirmed = current_rsi > 30  # Not oversold for short entries
            
            if settings.volume_confirmation and len(df) > 20:
                volume_series = df['volume']
                avg_volume = float(volume_series.rolling(window=20).mean().iloc[-1])
                current_volume = float(volume_series.iloc[-1])
                volume_confirmed = current_volume > avg_volume * 0.8  # At least 80% of average
            
            if rsi_confirmed and volume_confirmed:
                strength_val = "strong" if level in [0.618, 0.786] else "medium"
                
                # Consistent description without support/resistance confusion
                description = f"⚡ Golden Zone {zone_type.capitalize()} ({level:.3f} Fib)"
                
                results.append(FeatureResult(
                    module="fibonacci",
                    symbol="UNKNOWN",  # Will be filled by the scanner
                    timeframe="UNKNOWN",  # Will be filled by the scanner
                    candle_ts=int(datetime.now().timestamp()),
                    direction=direction,
                    strength=strength_val,
                    score=70 if strength_val == "strong" else 50,
                    reasons=[description],
                    levels={
                        'fib_level': level,
                        'actual_level': fib_level,
                        'deviation': deviation,
                        'rsi_confirmed': rsi_confirmed,
                        'volume_confirmed': volume_confirmed,
                        'fib_hit_ratio': level,
                        'is_golden_zone': True,
                        'zone_low': zone_low,
                        'zone_high': zone_high,
                        'zone_type': zone_type,
                        'swing_direction': swing_direction,
                        'swing_low': swing_low,
                        'swing_high': swing_high,
                        'hit_price': current_price
                    }
                ))
    
    return results


def detect_golden_ratio_patterns(df: pd.DataFrame) -> List[FeatureResult]:
    """
    Specialized function to detect Golden Ratio (0.618, 1.618) specific patterns
    """
    if len(df) < 100:
        return []
    
    results = []
    current_price = df['close'].iloc[-1]
    
    # Calculate based on highest high and lowest low in the period
    highest_high = df['high'].rolling(window=50).max()
    lowest_low = df['low'].rolling(window=50).min()
    
    for i in range(len(df)-10, len(df)):  # Check last 10 candles
        hh = highest_high.iloc[i]
        ll = lowest_low.iloc[i]
        
        if pd.isna(hh) or pd.isna(ll) or hh <= ll:
            continue
            
        range_val = hh - ll
        
        # Golden ratio levels
        golden_support = ll + (range_val * 0.618)
        golden_resistance = ll + (range_val * 0.382)
        
        price_at_candle = df['close'].iloc[i]
        
        # Check for golden ratio touches
        if abs(price_at_candle - golden_support) / price_at_candle < 0.005:
            results.append(FeatureResult(
                module="fibonacci",
                symbol="UNKNOWN",  # Will be filled by the scanner
                timeframe="UNKNOWN",  # Will be filled by the scanner
                candle_ts=int(datetime.now().timestamp()),
                direction="long",
                strength="strong",
                score=80,
                reasons=[f"🌟 GOLDEN RATIO TOUCH: Price touched golden support at {golden_support:.4f}"],
                levels={
                    'level': 0.618,
                    'actual_level': golden_support,
                    'candle_index': i
                }
            ))
        
        if abs(price_at_candle - golden_resistance) / price_at_candle < 0.005:
            results.append(FeatureResult(
                module="fibonacci",
                symbol="UNKNOWN",  # Will be filled by the scanner
                timeframe="UNKNOWN",  # Will be filled by thescanner
                candle_ts=int(datetime.now().timestamp()),
                direction="short",
                strength="strong",
                score=80,
                reasons=[f"🌟 GOLDEN RATIO TOUCH: Price touched golden resistance at {golden_resistance:.4f}"],
                levels={
                    'level': 0.382,
                    'actual_level': golden_resistance,
                    'candle_index': i
                }
            ))
    
    return results


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None) -> List[FeatureResult]:
    """
    Main analysis function for the Fibonacci module
    """
    # Handle settings parameter correctly
    if settings is None:
        fib_settings = FibonacciSettings()
    elif isinstance(settings, FibonacciSettings):
        fib_settings = settings
    else:
        # If it's a dict, create FibonacciSettings with those values
        fib_settings = FibonacciSettings(**settings)
    
    all_results = []
    
    # Standard Fibonacci analysis
    all_results.extend(fibonacci_analysis(df, fib_settings))
    
    # Golden ratio specific patterns
    all_results.extend(detect_golden_ratio_patterns(df))
    
    return all_results