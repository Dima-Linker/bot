"""
PUMP/Momentum Scanner Module for the Crypto-Signal Hub-Bot
Detects strong price moves, volume spikes, and breakout patterns
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class PumpSettings:
    """Settings for Pump/Momentum detection"""
    enabled: bool = True
    price_change_threshold: float = 2.0  # 2% minimum move
    volume_spike_threshold: float = 3.0  # 3x average volume
    timeframe_windows: List[str] = None  # ['5m', '15m', '1h']
    rsi_extreme_threshold: float = 80.0  # RSI overbought/oversold
    min_candles_for_trend: int = 5  # Minimum candles to confirm trend
    breakout_range_multiplier: float = 1.5  # Range expansion factor
    
    def __post_init__(self):
        if self.timeframe_windows is None:
            self.timeframe_windows = ['5m', '15m']


def calculate_price_changes(df: pd.DataFrame, windows: List[str]) -> Dict[str, float]:
    """Calculate price changes over different time windows"""
    changes = {}
    
    for window_str in windows:
        # Convert string to number of candles (approximate)
        if window_str == '5m':
            candles = 1
        elif window_str == '15m':
            candles = 3
        elif window_str == '1h':
            candles = 12
        else:
            candles = 4  # default 15m equivalent
        
        if len(df) > candles:
            current_price = df['close'].iloc[-1]
            past_price = df['close'].iloc[-(candles + 1)]
            change_pct = ((current_price - past_price) / past_price) * 100
            changes[window_str] = change_pct
        else:
            changes[window_str] = 0.0
    
    return changes


def calculate_volume_metrics(df: pd.DataFrame, lookback: int = 20) -> Dict[str, float]:
    """Calculate volume-related metrics"""
    if len(df) < lookback:
        return {'current_volume': 0, 'avg_volume': 0, 'volume_ratio': 0}
    
    current_volume = float(df['volume'].iloc[-1])
    avg_volume = float(df['volume'].rolling(window=lookback).mean().iloc[-1])
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
    
    return {
        'current_volume': current_volume,
        'avg_volume': avg_volume,
        'volume_ratio': volume_ratio
    }


def calculate_rsi(close_prices: pd.Series, window: int = 14) -> float:
    """Calculate current RSI value"""
    if len(close_prices) < window + 1:
        return 50.0
    
    delta = close_prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0


def detect_breakout(df: pd.DataFrame, lookback: int = 20) -> Optional[Dict]:
    """Detect breakout from range"""
    if len(df) < lookback:
        return None
    
    # Calculate recent range
    recent_high = df['high'].iloc[-lookback:].max()
    recent_low = df['low'].iloc[-lookback:].min()
    current_price = df['close'].iloc[-1]
    
    # Check for breakout
    upper_breakout = current_price > recent_high
    lower_breakout = current_price < recent_low
    
    if upper_breakout or lower_breakout:
        range_size = recent_high - recent_low
        breakout_strength = abs(current_price - (recent_high if upper_breakout else recent_low)) / range_size
        
        return {
            'type': 'upper' if upper_breakout else 'lower',
            'strength': breakout_strength,
            'range_high': float(recent_high),
            'range_low': float(recent_low),
            'breakout_price': float(current_price)
        }
    
    return None


def detect_pump_signal(df: pd.DataFrame, settings: PumpSettings, symbol: str, timeframe: str) -> Optional[FeatureResult]:
    """Main pump detection function"""
    if len(df) < 20 or not settings.enabled:
        return None
    
    # Calculate metrics
    price_changes = calculate_price_changes(df, settings.timeframe_windows)
    volume_metrics = calculate_volume_metrics(df)
    current_rsi = calculate_rsi(df['close'])
    breakout_info = detect_breakout(df)
    
    # Check for pump conditions
    pump_signals = []
    total_score = 0
    
    # 1. Price Change Detection
    for window, change in price_changes.items():
        if abs(change) >= settings.price_change_threshold:
            pump_signals.append(f"{window}: {change:+.2f}%")
            # Score based on magnitude
            score_contribution = min(abs(change) * 10, 30)
            if change > 0:
                total_score += score_contribution
            else:
                total_score += score_contribution * 0.7  # Bearish moves get slightly lower score
    
    # 2. Volume Spike Detection
    if volume_metrics['volume_ratio'] >= settings.volume_spike_threshold:
        pump_signals.append(f"Vol spike: {volume_metrics['volume_ratio']:.1f}x avg")
        total_score += 25
    
    # 3. RSI Extreme Detection
    if current_rsi >= settings.rsi_extreme_threshold or current_rsi <= (100 - settings.rsi_extreme_threshold):
        direction = "overbought" if current_rsi >= settings.rsi_extreme_threshold else "oversold"
        pump_signals.append(f"RSI extreme: {current_rsi:.1f} ({direction})")
        total_score += 15
    
    # 4. Breakout Detection
    if breakout_info:
        pump_signals.append(f"Breakout {breakout_info['type']}: {breakout_info['strength']:.2f}x range")
        total_score += 20 * breakout_info['strength']
    
    # Determine direction
    avg_change = sum(price_changes.values()) / len(price_changes) if price_changes else 0
    direction = "long" if avg_change > 0 else "short"
    
    # Apply minimum score threshold
    if total_score >= 40 and pump_signals:  # Minimum quality threshold
        return FeatureResult(
            module="pump",
            symbol=symbol,
            timeframe=timeframe,
            candle_ts=int(df.iloc[-1]['timestamp']) if 'timestamp' in df.columns else int(datetime.now().timestamp()),
            direction=direction,
            strength="strong" if total_score >= 80 else "medium",
            score=min(int(total_score), 100),
            event="PUMP_ALERT",
            levels={
                'price_changes': price_changes,
                'volume_ratio': volume_metrics['volume_ratio'],
                'rsi': current_rsi,
                'breakout': breakout_info,
                'current_price': float(df['close'].iloc[-1])
            },
            reasons=pump_signals[:3]  # Top 3 strongest signals
        )
    
    return None


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None, symbol: str = "UNKNOWN", timeframe: str = "UNKNOWN") -> List[FeatureResult]:
    """Main analysis function for Pump module"""
    # Handle settings
    if settings is None:
        pump_settings = PumpSettings()
    elif isinstance(settings, PumpSettings):
        pump_settings = settings
    else:
        pump_settings = PumpSettings(**settings)
    
    # Detect pump signal
    pump_result = detect_pump_signal(df, pump_settings, symbol, timeframe)
    
    return [pump_result] if pump_result else []


# Export for module registry
__all__ = ['PumpSettings', 'analyze', 'detect_pump_signal']