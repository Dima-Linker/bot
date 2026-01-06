"""
Volume Module for the Crypto-Signal Hub-Bot
Detects unusual volume activity and potential signals
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class VolumeSettings:
    """Settings for volume analysis"""
    enabled: bool = True
    volume_threshold: float = 2.0  # How many times above average volume
    min_price_change: float = 0.02  # Minimum 2% price change to qualify
    lookback_period: int = 20  # Look back this many candles for average volume


def detect_unusual_volume(df: pd.DataFrame, settings: VolumeSettings) -> List[FeatureResult]:
    """Detect unusual volume activity"""
    if len(df) < settings.lookback_period or settings.enabled is False:
        return []
    
    results = []
    
    # Calculate average volume
    avg_volume = df['volume'].rolling(window=settings.lookback_period).mean()
    current_volume = df['volume'].iloc[-1]
    current_close = df['close'].iloc[-1]
    current_high = df['high'].iloc[-1]
    current_low = df['low'].iloc[-1]
    
    # Check if volume is significantly above average
    if current_volume > avg_volume.iloc[-1] * settings.volume_threshold:
        # Calculate price change
        prev_close = df['close'].iloc[-2] if len(df) > 1 else current_close
        price_change = (current_close - prev_close) / prev_close
        
        # Determine direction based on price action
        direction: Direction = "long" if price_change > 0 else "short" if price_change < 0 else "both"
        
        # Determine strength based on volume multiple
        vol_multiple = current_volume / avg_volume.iloc[-1]
        if vol_multiple >= 5.0:
            strength: Strength = "elite"
        elif vol_multiple >= 3.0:
            strength: Strength = "strong"
        else:
            strength: Strength = "medium"
        
        # Calculate score based on volume multiple and price change
        base_score = int(min(95, 50 + (vol_multiple * 10) + abs(price_change * 100)))
        
        reasons = [f"Unusual volume detected: {vol_multiple:.1f}x average volume"]
        
        # Add more specific reasons based on price action
        if abs(price_change) >= settings.min_price_change:
            action = "BULLISH" if price_change > 0 else "BEARISH"
            reasons.append(f"{action} price action: {price_change:+.2%}")
        
        # Detect potential breakouts
        if current_high == df['high'].rolling(5).max().iloc[-1]:
            reasons.append("Potential bullish breakout")
            direction = "long"
        elif current_low == df['low'].rolling(5).min().iloc[-1]:
            reasons.append("Potential bearish breakdown")
            direction = "short"
        
        results.append(FeatureResult(
            module="volume",
            symbol="UNKNOWN",  # Will be filled by the scanner
            timeframe="UNKNOWN",  # Will be filled by the scanner
            candle_ts=int(datetime.now().timestamp()),
            direction=direction,
            strength=strength,
            score=base_score,
            reasons=reasons,
            levels={
                'volume_multiple': vol_multiple,
                'price_change': price_change,
                'current_volume': current_volume,
                'average_volume': avg_volume.iloc[-1]
            }
        ))
    
    return results


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None) -> List[FeatureResult]:
    """Main analysis function for the Volume module"""
    if settings is None:
        vol_settings = VolumeSettings()
    elif isinstance(settings, VolumeSettings):
        vol_settings = settings
    else:
        # If it's a dict, create VolumeSettings with those values
        vol_settings = VolumeSettings(**settings)
    
    all_results = []
    
    # Detect unusual volume
    all_results.extend(detect_unusual_volume(df, vol_settings))
    
    return all_results