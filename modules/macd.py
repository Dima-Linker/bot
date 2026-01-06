"""
MACD Module for the Crypto-Signal Hub-Bot
Detects MACD crossovers, divergences, and momentum shifts
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class MACDSettings:
    """Settings for MACD analysis"""
    enabled: bool = True
    fast_period: int = 12
    slow_period: int = 26
    signal_period: int = 9
    min_histogram_change: float = 0.0001  # Minimum change to consider a signal
    min_consecutive_bars: int = 2  # Minimum consecutive bars for trend confirmation
    max_signals_per_type: int = 2  # Maximum signals to return per type


def calculate_macd(df: pd.DataFrame, settings: MACDSettings):
    """Calculate MACD values"""
    close_prices = df['close']
    
    # Calculate EMAs
    ema_fast = close_prices.ewm(span=settings.fast_period).mean()
    ema_slow = close_prices.ewm(span=settings.slow_period).mean()
    
    # Calculate MACD line
    macd_line = ema_fast - ema_slow
    
    # Calculate signal line
    signal_line = macd_line.ewm(span=settings.signal_period).mean()
    
    # Calculate histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def detect_macd_crossovers(df: pd.DataFrame, settings: MACDSettings) -> List[FeatureResult]:
    """Detect MACD crossovers (signal line crosses MACD line)"""
    if len(df) < max(settings.fast_period, settings.slow_period, settings.signal_period) + 10:
        return []

    macd_line, signal_line, histogram = calculate_macd(df, settings)
    
    crossovers = []
    current_price = df['close'].iloc[-1]
    
    # Look for crossovers in recent candles to avoid false signals
    for i in range(len(df)-10, len(df)-1):  # Check last 10 candles
        # Bullish crossover: MACD line crosses above signal line
        if (i > 0 and 
            histogram.iloc[i-1] < 0 and  # Was negative (bearish)
            histogram.iloc[i] > 0 and   # Now positive (bullish)
            macd_line.iloc[i-1] <= signal_line.iloc[i-1] and  # MACD below signal before
            macd_line.iloc[i] > signal_line.iloc[i]):         # MACD above signal now
            
            # Check if there was sufficient downtrend before for a meaningful reversal
            lookback = min(20, i)
            prev_macd_values = histogram.iloc[i-lookback:i]
            has_downtrend = (prev_macd_values < 0).sum() > lookback * 0.6  # 60% were negative
            
            # Calculate distance to current price based on signal significance
            histogram_change = abs(histogram.iloc[i] - histogram.iloc[i-1])
            distance = 0.01  # Default distance for MACD
            
            score = 60
            strength = 'medium'
            if histogram_change > settings.min_histogram_change * 2:
                score = 80
                strength = 'strong'
            elif histogram_change > settings.min_histogram_change:
                score = 70
                strength = 'medium'
            
            # Boost score if there was a clear downtrend before
            if has_downtrend:
                score += 15
                if strength == 'medium':
                    strength = 'strong'
            
            crossovers.append(FeatureResult(
                module='macd',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='long',
                strength=strength,
                score=score,
                reasons=[f"Bullish MACD crossover at {df['close'].iloc[i]:.5f}"],
                levels={'macd_value': float(macd_line.iloc[i]), 'signal_value': float(signal_line.iloc[i]), 'histogram': float(histogram.iloc[i])}
            ))
        
        # Bearish crossover: MACD line crosses below signal line
        if (i > 0 and 
            histogram.iloc[i-1] > 0 and  # Was positive (bullish)
            histogram.iloc[i] < 0 and   # Now negative (bearish)
            macd_line.iloc[i-1] >= signal_line.iloc[i-1] and  # MACD above signal before
            macd_line.iloc[i] < signal_line.iloc[i]):         # MACD below signal now
            
            # Check if there was sufficient uptrend before for a meaningful reversal
            lookback = min(20, i)
            prev_macd_values = histogram.iloc[i-lookback:i]
            has_uptrend = (prev_macd_values > 0).sum() > lookback * 0.6  # 60% were positive
            
            # Calculate distance to current price based on signal significance
            histogram_change = abs(histogram.iloc[i-1] - histogram.iloc[i])
            distance = 0.01  # Default distance for MACD
            
            score = 60
            strength = 'medium'
            if histogram_change > settings.min_histogram_change * 2:
                score = 80
                strength = 'strong'
            elif histogram_change > settings.min_histogram_change:
                score = 70
                strength = 'medium'
            
            # Boost score if there was a clear uptrend before
            if has_uptrend:
                score += 15
                if strength == 'medium':
                    strength = 'strong'
            
            crossovers.append(FeatureResult(
                module='macd',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='short',
                strength=strength,
                score=score,
                reasons=[f"Bearish MACD crossover at {df['close'].iloc[i]:.5f}"],
                levels={'macd_value': float(macd_line.iloc[i]), 'signal_value': float(signal_line.iloc[i]), 'histogram': float(histogram.iloc[i])}
            ))
    
    # Sort by most recent and return top signals
    crossovers.sort(key=lambda x: x.score, reverse=True)
    return crossovers[:settings.max_signals_per_type]


def detect_zero_line_crossovers(df: pd.DataFrame, settings: MACDSettings) -> List[FeatureResult]:
    """Detect MACD line crossing zero line (for momentum shifts)"""
    if len(df) < max(settings.fast_period, settings.slow_period, settings.signal_period) + 10:
        return []

    macd_line, signal_line, histogram = calculate_macd(df, settings)
    
    zero_crossings = []
    
    for i in range(len(df)-10, len(df)-1):  # Check last 10 candles
        # Bullish zero line cross: MACD line crosses from negative to positive
        if (i > 0 and 
            macd_line.iloc[i-1] < 0 and  # Was negative
            macd_line.iloc[i] > 0):      # Now positive
            
            score = 50
            strength = 'weak'
            # Check histogram for strength
            if histogram.iloc[i] > settings.min_histogram_change:
                score = 70
                strength = 'medium'
            elif histogram.iloc[i] > settings.min_histogram_change * 2:
                score = 85
                strength = 'strong'
            
            zero_crossings.append(FeatureResult(
                module='macd',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='long',
                strength=strength,
                score=score,
                reasons=[f"MACD bullish zero line cross at {df['close'].iloc[i]:.5f}"],
                levels={'macd_value': float(macd_line.iloc[i]), 'signal_value': float(signal_line.iloc[i]), 'histogram': float(histogram.iloc[i])}
            ))
        
        # Bearish zero line cross: MACD line crosses from positive to negative
        if (i > 0 and 
            macd_line.iloc[i-1] > 0 and  # Was positive
            macd_line.iloc[i] < 0):      # Now negative
            
            score = 50
            strength = 'weak'
            # Check histogram for strength
            if abs(histogram.iloc[i]) > settings.min_histogram_change:
                score = 70
                strength = 'medium'
            elif abs(histogram.iloc[i]) > settings.min_histogram_change * 2:
                score = 85
                strength = 'strong'
            
            zero_crossings.append(FeatureResult(
                module='macd',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='short',
                strength=strength,
                score=score,
                reasons=[f"MACD bearish zero line cross at {df['close'].iloc[i]:.5f}"],
                levels={'macd_value': float(macd_line.iloc[i]), 'signal_value': float(signal_line.iloc[i]), 'histogram': float(histogram.iloc[i])}
            ))
    
    # Sort by most recent and return top signals
    zero_crossings.sort(key=lambda x: x.score, reverse=True)
    return zero_crossings[:settings.max_signals_per_type]


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None) -> List[FeatureResult]:
    """Analyze DataFrame for MACD patterns"""
    if settings is None:
        macd_settings = MACDSettings()
    elif isinstance(settings, MACDSettings):
        macd_settings = settings
    else:
        # If it's a dict, create MACDSettings with those values
        macd_settings = MACDSettings(**settings)

    all_results = []
    
    # Detect MACD patterns
    all_results.extend(detect_macd_crossovers(df, macd_settings))
    all_results.extend(detect_zero_line_crossovers(df, macd_settings))
    
    # Sort by score (highest first) and return only the top ones
    all_results.sort(key=lambda x: x.score, reverse=True)
    return all_results[:macd_settings.max_signals_per_type * 2]  # 2 types of MACD signals