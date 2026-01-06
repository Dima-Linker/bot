"""
SMC (Smart Money Concepts) Module for the Crypto-Signal Hub-Bot
Detects Order Blocks, Fair Value Gaps, and Break of Structure
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime

from engine.types import FeatureResult, Direction, Strength


@dataclass
class SMCSettings:
    """Settings for SMC analysis"""
    enabled: bool = True
    order_block_min_range: float = 0.002  # 0.2% minimum range for order blocks
    fvg_min_range: float = 0.001  # 0.1% minimum range for FVG
    lookback_period: int = 20  # Look back this many candles for SMC patterns
    min_volume_confirmation: float = 1.5  # Volume must be 1.5x average for confirmation
    max_zones_per_type: int = 2  # Maximum zones to return per type


def detect_order_blocks(df: pd.DataFrame, settings: SMCSettings) -> List[FeatureResult]:
    """Detect Order Blocks (high-probability reversal zones)"""
    if len(df) < settings.lookback_period or settings.lookback_period < 3:
        return []

    order_blocks = []
    current_price = df['close'].iloc[-1]
    
    # Look for potential order blocks by finding swing points
    for i in range(settings.lookback_period, len(df)-2):
        # Bullish order block: price made a low, then reversed up strongly
        if (df['low'].iloc[i] <= df['low'].iloc[i-2:i+2].min() and 
            df['close'].iloc[i+1] > df['high'].iloc[i] and
            (df['high'].iloc[i] - df['low'].iloc[i]) / df['low'].iloc[i] >= settings.order_block_min_range):
            
            # Calculate distance to current price
            distance = abs(current_price - df['high'].iloc[i]) / current_price
            
            score = 50
            strength = 'weak'
            if distance < 0.02:  # Within 2%
                score = 80
                strength = 'strong'
            elif distance < 0.05:  # Within 5%
                score = 70
                strength = 'medium'
            
            # Check volume confirmation
            avg_vol_series = df['volume'].rolling(20).mean()
            avg_vol_val = avg_vol_series.iloc[i] if isinstance(avg_vol_series, pd.Series) else avg_vol_series[i]
            if avg_vol_val > 0 and df['volume'].iloc[i+1] > avg_vol_val * settings.min_volume_confirmation:
                score += 20
                if strength == 'weak':
                    strength = 'medium'
                elif strength == 'medium':
                    strength = 'strong'
            
            order_blocks.append(FeatureResult(
                module='smc',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='long',
                strength=strength,
                score=score,
                reasons=[f"Bullish Order Block at {df['high'].iloc[i]:.5f}"],
                levels={
                    'order_block_high': float(df['high'].iloc[i]), 
                    'distance': distance,
                    'sweep_high': float(df['high'].iloc[i]),
                    'reclaim_close': True  # Since it reversed up strongly
                }
            ))
        
        # Bearish order block: price made a high, then reversed down strongly
        if (df['high'].iloc[i] >= df['high'].iloc[i-2:i+2].max() and 
            df['close'].iloc[i+1] < df['low'].iloc[i] and
            (df['high'].iloc[i] - df['low'].iloc[i]) / df['low'].iloc[i] >= settings.order_block_min_range):
            
            # Calculate distance to current price
            distance = abs(current_price - df['low'].iloc[i]) / current_price
            
            score = 50
            strength = 'weak'
            if distance < 0.02:  # Within 2%
                score = 80
                strength = 'strong'
            elif distance < 0.05:  # Within 5%
                score = 70
                strength = 'medium'
            
            # Check volume confirmation
            avg_vol_series = df['volume'].rolling(20).mean()
            avg_vol_val = avg_vol_series.iloc[i] if isinstance(avg_vol_series, pd.Series) else avg_vol_series[i]
            if avg_vol_val > 0 and df['volume'].iloc[i+1] > avg_vol_val * settings.min_volume_confirmation:
                score += 20
                if strength == 'weak':
                    strength = 'medium'
                elif strength == 'medium':
                    strength = 'strong'
            
            order_blocks.append(FeatureResult(
                module='smc',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='short',
                strength=strength,
                score=score,
                reasons=[f"Bearish Order Block at {df['low'].iloc[i]:.5f}"],
                levels={
                    'order_block_low': float(df['low'].iloc[i]), 
                    'distance': distance,
                    'sweep_low': float(df['low'].iloc[i]),
                    'reclaim_close': True  # Since it reversed down strongly
                }
            ))
    
    # Sort by distance to current price (closest first) and return top N
    order_blocks.sort(key=lambda x: x.levels['distance'] if x.levels and 'distance' in x.levels else float('inf'))
    return order_blocks[:settings.max_zones_per_type]


def detect_fvg(df: pd.DataFrame, settings: SMCSettings, target_direction: Optional[str] = None) -> List[FeatureResult]:
    """Detect Fair Value Gaps (imbalances in price action)"""
    if len(df) < settings.lookback_period:
        return []

    fvgs = []
    current_price = df['close'].iloc[-1]
    
    for i in range(settings.lookback_period, len(df)-2):
        # FVG: gap between high of one candle and low of the next (or vice versa)
        # Bullish FVG: gap between previous candle's high and next candle's low
        if i > 0 and df['low'].iloc[i-1] > df['high'].iloc[i+1]:  # Gap down
            gap_size = (df['low'].iloc[i-1] - df['high'].iloc[i+1]) / df['high'].iloc[i+1]
            if gap_size >= settings.fvg_min_range:
                # Only add if direction matches target_direction or no target_direction specified
                if target_direction is None or target_direction == 'long':
                    # Calculate distance to current price
                    distance = abs(current_price - (df['low'].iloc[i-1] + df['high'].iloc[i+1]) / 2) / current_price
                    
                    score = 40
                    strength = 'weak'
                    if distance < 0.02:  # Within 2%
                        score = 70
                        strength = 'strong'
                    elif distance < 0.05:  # Within 5%
                        score = 60
                        strength = 'medium'
                    
                    fvgs.append(FeatureResult(
                        module='smc',
                        symbol='',
                        timeframe='',
                        candle_ts=0,
                        direction='long',
                        strength=strength,
                        score=score,
                        reasons=[f"Bullish FVG: {df['high'].iloc[i+1]:.5f} - {df['low'].iloc[i-1]:.5f}"],
                        levels={'fvg_low': float(df['high'].iloc[i+1]), 'fvg_high': float(df['low'].iloc[i-1]), 'distance': distance}
                    ))
        
        # Bearish FVG: gap between previous candle's low and next candle's high
        elif i > 0 and df['high'].iloc[i-1] < df['low'].iloc[i+1]:  # Gap up
            gap_size = (df['low'].iloc[i+1] - df['high'].iloc[i-1]) / df['high'].iloc[i-1]
            if gap_size >= settings.fvg_min_range:
                # Only add if direction matches target_direction or no target_direction specified
                if target_direction is None or target_direction == 'short':
                    # Calculate distance to current price
                    distance = abs(current_price - (df['high'].iloc[i-1] + df['low'].iloc[i+1]) / 2) / current_price
                    
                    score = 40
                    strength = 'weak'
                    if distance < 0.02:  # Within 2%
                        score = 70
                        strength = 'strong'
                    elif distance < 0.05:  # Within 5%
                        score = 60
                        strength = 'medium'
                    
                    fvgs.append(FeatureResult(
                        module='smc',
                        symbol='',
                        timeframe='',
                        candle_ts=0,
                        direction='short',
                        strength=strength,
                        score=score,
                        reasons=[f"Bearish FVG: {df['high'].iloc[i-1]:.5f} - {df['low'].iloc[i+1]:.5f}"],
                        levels={'fvg_low': float(df['high'].iloc[i-1]), 'fvg_high': float(df['low'].iloc[i+1]), 'distance': distance}
                    ))
    
    # Sort by distance to current price (closest first) and return top N
    fvgs.sort(key=lambda x: x.levels['distance'] if x.levels and 'distance' in x.levels else float('inf'))
    return fvgs[:settings.max_zones_per_type]


def detect_bos_choch(df: pd.DataFrame, settings: SMCSettings) -> List[FeatureResult]:
    """Detect Break of Structure and Change of Character"""
    if len(df) < settings.lookback_period:
        return []

    bos_choch_signals = []
    current_price = df['close'].iloc[-1]
    
    # Simplified detection of swing highs/lows
    for i in range(settings.lookback_period, len(df)-5):
        # Find swing high (BOS up / CHoCH down)
        if (df['high'].iloc[i] >= df['high'].iloc[i-2:i+3].max() and 
            df['high'].iloc[i+2] > df['high'].iloc[i]):  # Break of swing high
            distance = abs(current_price - df['high'].iloc[i]) / current_price
            score = 35
            strength = 'weak'
            if distance < 0.02:
                score = 65
                strength = 'strong'
            elif distance < 0.05:
                score = 55
                strength = 'medium'
                
            bos_choch_signals.append(FeatureResult(
                module='smc',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='long',
                strength=strength,
                score=score,
                reasons=[f"BOS up at {df['high'].iloc[i]:.5f}"],
                levels={
                    'bos_high': float(df['high'].iloc[i]), 
                    'distance': distance,
                    'choch_confirmed': True,
                    'broken_level': float(df['high'].iloc[i]),
                    'break_and_close': True
                }
            ))
        
        # Find swing low (BOS down / CHoCH up)
        if (df['low'].iloc[i] <= df['low'].iloc[i-2:i+3].min() and 
            df['low'].iloc[i+2] < df['low'].iloc[i]):  # Break of swing low
            distance = abs(current_price - df['low'].iloc[i]) / current_price
            score = 35
            strength = 'weak'
            if distance < 0.02:
                score = 65
                strength = 'strong'
            elif distance < 0.05:
                score = 55
                strength = 'medium'
                
            bos_choch_signals.append(FeatureResult(
                module='smc',
                symbol='',
                timeframe='',
                candle_ts=0,
                direction='short',
                strength=strength,
                score=score,
                reasons=[f"BOS down at {df['low'].iloc[i]:.5f}"],
                levels={
                    'bos_low': float(df['low'].iloc[i]), 
                    'distance': distance,
                    'choch_confirmed': True,
                    'broken_level': float(df['low'].iloc[i]),
                    'break_and_close': True
                }
            ))
    
    # Sort by distance to current price (closest first) and return top N
    bos_choch_signals.sort(key=lambda x: x.levels['distance'] if x.levels and 'distance' in x.levels else float('inf'))
    return bos_choch_signals[:settings.max_zones_per_type]


def analyze(df: pd.DataFrame, settings: Optional[Dict] = None, target_direction: Optional[str] = None) -> List[FeatureResult]:
    """Analyze DataFrame for SMC patterns"""
    if settings is None:
        smc_settings = SMCSettings()
    elif isinstance(settings, SMCSettings):
        smc_settings = settings
    else:
        # If it's a dict, create SMCSettings with those values
        smc_settings = SMCSettings(**settings)

    all_results = []
    
    # Detect all SMC patterns
    all_results.extend(detect_order_blocks(df, smc_settings))
    all_results.extend(detect_fvg(df, smc_settings, target_direction))
    all_results.extend(detect_bos_choch(df, smc_settings))
    
    # Sort by score (highest first) and return only the top ones
    all_results.sort(key=lambda x: x.score, reverse=True)
    return all_results[:smc_settings.max_zones_per_type * 3]  # 3 types of SMC patterns