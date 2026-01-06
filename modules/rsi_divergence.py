"""
RSI Divergence Module for the Crypto-Signal Hub-Bot
Detects bullish and bearish RSI divergences
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class RSIDivergenceSettings:
    """Settings for RSI divergence analysis"""
    enabled: bool = True
    rsi_period: int = 14
    min_rsi: int = 30  # Minimum RSI for bullish divergence
    max_rsi: int = 70  # Maximum RSI for bearish divergence
    min_price_change: float = 0.02  # Minimum 2% price change to qualify
    min_rsi_change: int = 15  # Minimum RSI change to qualify
    lookback_period: int = 50  # Look back this many candles for swing points


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return pd.Series(rsi)


def find_swing_highs_lows(series: pd.Series, window: int = 5) -> pd.DataFrame:
    """Find swing highs and lows in a series"""
    df = pd.DataFrame({'value': series})
    
    # Find local maxima (swing highs)
    df['swing_high'] = (
        (df['value'] > df['value'].shift(1)) & 
        (df['value'] > df['value'].shift(-1)) &
        (df['value'] > df['value'].shift(2)) & 
        (df['value'] > df['value'].shift(-2))
    )
    
    # Find local minima (swing lows)  
    df['swing_low'] = (
        (df['value'] < df['value'].shift(1)) & 
        (df['value'] < df['value'].shift(-1)) &
        (df['value'] < df['value'].shift(2)) & 
        (df['value'] < df['value'].shift(-2))
    )
    
    return df


def detect_bullish_divergence(prices: pd.Series, rsi_values: pd.Series, 
                             settings: RSIDivergenceSettings) -> List[FeatureResult]:
    """Detect bullish divergence (price makes lower low, RSI makes higher low)"""
    results = []
    
    # Find swing lows in both price and RSI
    price_swings = find_swing_lows(prices)
    rsi_swings = find_swing_lows(rsi_values)
    
    # Look for pairs of swing lows to compare
    swing_lows = price_swings[price_swings['swing_low']].index.tolist()
    rsi_lows = rsi_swings[rsi_swings['swing_low']].index.tolist()
    
    for i in range(1, len(swing_lows)):
        # Current and previous swing low in price
        current_price_idx = swing_lows[i]
        prev_price_idx = swing_lows[i-1]
        
        if current_price_idx in rsi_lows and prev_price_idx in rsi_lows:
            current_price = prices.iloc[current_price_idx]
            prev_price = prices.iloc[prev_price_idx]
            current_rsi = rsi_values.iloc[current_price_idx]
            prev_rsi = rsi_values.iloc[prev_price_idx]
            
            # Bullish divergence: price makes lower low, RSI makes higher low
            if (current_price < prev_price and  # Lower price low
                current_rsi > prev_rsi and      # Higher RSI low
                current_rsi < settings.min_rsi): # RSI in oversold zone
                
                price_change = (current_price - prev_price) / prev_price
                rsi_change = current_rsi - prev_rsi
                
                if abs(price_change) >= settings.min_price_change and rsi_change >= settings.min_rsi_change:
                    results.append(FeatureResult(
                        module="rsi_divergence",
                        symbol="UNKNOWN",  # Will be filled by the scanner
                        timeframe="UNKNOWN",  # Will be filled by the scanner
                        candle_ts=int(datetime.now().timestamp()),
                        direction="long",
                        strength="strong",
                        score=85,
                        reasons=[f"🟢 BULLISH DIVERGENCE: Price made lower low ({prev_price:.4f} → {current_price:.4f}) but RSI made higher low ({prev_rsi:.1f} → {current_rsi:.1f})"],
                        levels={
                            'price_change': price_change,
                            'rsi_change': rsi_change,
                            'current_price_idx': int(current_price_idx),
                            'prev_price_idx': int(prev_price_idx),
                            'current_rsi': current_rsi,
                            'prev_rsi': prev_rsi
                        }
                    ))
    
    return results


def detect_bearish_divergence(prices: pd.Series, rsi_values: pd.Series, 
                             settings: RSIDivergenceSettings) -> List[FeatureResult]:
    """Detect bearish divergence (price makes higher high, RSI makes lower high)"""
    results = []
    
    # Find swing highs in both price and RSI
    price_swings = find_swing_highs(prices)
    rsi_swings = find_swing_highs(rsi_values)
    
    # Look for pairs of swing highs to compare
    swing_highs = price_swings[price_swings['swing_high']].index.tolist()
    rsi_highs = rsi_swings[rsi_swings['swing_high']].index.tolist()
    
    for i in range(1, len(swing_highs)):
        # Current and previous swing high in price
        current_price_idx = swing_highs[i]
        prev_price_idx = swing_highs[i-1]
        
        if current_price_idx in rsi_highs and prev_price_idx in rsi_highs:
            current_price = prices.iloc[current_price_idx]
            prev_price = prices.iloc[prev_price_idx]
            current_rsi = rsi_values.iloc[current_price_idx]
            prev_rsi = rsi_values.iloc[prev_price_idx]
            
            # Bearish divergence: price makes higher high, RSI makes lower high
            if (current_price > prev_price and  # Higher price high
                current_rsi < prev_rsi and      # Lower RSI high
                current_rsi > settings.max_rsi): # RSI in overbought zone
                
                price_change = (current_price - prev_price) / prev_price
                rsi_change = prev_rsi - current_rsi
                
                if abs(price_change) >= settings.min_price_change and rsi_change >= settings.min_rsi_change:
                    results.append(FeatureResult(
                        module="rsi_divergence",
                        symbol="UNKNOWN",  # Will be filled by the scanner
                        timeframe="UNKNOWN",  # Will be filled by the scanner
                        candle_ts=int(datetime.now().timestamp()),
                        direction="short",
                        strength="strong",
                        score=85,
                        reasons=[f"🔴 BEARISH DIVERGENCE: Price made higher high ({prev_price:.4f} → {current_price:.4f}) but RSI made lower high ({prev_rsi:.1f} → {current_rsi:.1f})"],
                        levels={
                            'price_change': price_change,
                            'rsi_change': rsi_change,
                            'current_price_idx': int(current_price_idx),
                            'prev_price_idx': int(prev_price_idx),
                            'current_rsi': current_rsi,
                            'prev_rsi': prev_rsi
                        }
                    ))
    
    return results


def find_swing_highs(series: pd.Series, window: int = 5) -> pd.DataFrame:
    """Find swing highs in a series"""
    df = pd.DataFrame({'value': series})
    
    # Find local maxima (swing highs)
    df['swing_high'] = (
        (df['value'] > df['value'].shift(1)) & 
        (df['value'] > df['value'].shift(-1)) &
        (df['value'] > df['value'].shift(2)) & 
        (df['value'] > df['value'].shift(-2))
    )
    
    return df


def find_swing_lows(series: pd.Series, window: int = 5) -> pd.DataFrame:
    """Find swing lows in a series"""
    df = pd.DataFrame({'value': series})
    
    # Find local minima (swing lows)  
    df['swing_low'] = (
        (df['value'] < df['value'].shift(1)) & 
        (df['value'] < df['value'].shift(-1)) &
        (df['value'] < df['value'].shift(2)) & 
        (df['value'] < df['value'].shift(-2))
    )
    
    return df


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None) -> List[FeatureResult]:
    """Main analysis function for the RSI Divergence module"""
    if settings is None:
        rsi_settings = RSIDivergenceSettings()
    elif isinstance(settings, RSIDivergenceSettings):
        rsi_settings = settings
    else:
        # If it's a dict, create RSIDivergenceSettings with those values
        rsi_settings = RSIDivergenceSettings(**settings)
    
    if len(df) < rsi_settings.lookback_period or rsi_settings.enabled is False:
        return []
    
    results = []
    
    # Calculate RSI
    rsi = calculate_rsi(df['close'], rsi_settings.rsi_period)
    
    # Detect bullish divergences
    bullish_divs = detect_bullish_divergence(df['close'], rsi, rsi_settings)
    results.extend(bullish_divs)
    
    # Detect bearish divergences
    bearish_divs = detect_bearish_divergence(df['close'], rsi, rsi_settings)
    results.extend(bearish_divs)
    
    return results