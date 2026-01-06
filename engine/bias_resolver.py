"""Multi-Timeframe Bias Resolver for consistent signal routing"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Optional, Tuple
import numpy as np

class MarketBias(Enum):
    BULL = "BULL"
    BEAR = "BEAR" 
    NEUTRAL = "NEUTRAL"

class BiasResolver:
    """Resolves market bias across timeframes (4h -> 1h -> 15m)"""
    
    def __init__(self):
        self.bias_cache: Dict[str, Dict[str, MarketBias]] = {}
    
    def resolve_bias(self, symbol: str, candles_4h: list, candles_1h: list, candles_15m: list) -> Dict[str, MarketBias]:
        """
        Resolve bias for all timeframes
        Returns dict with '4h', '1h', '15m' keys
        """
        bias_result = {}
        
        # 4h Bias (Primary Trend)
        bias_result['4h'] = self._calculate_4h_bias(candles_4h)
        
        # 1h Bias (Intermediate Filter)  
        bias_result['1h'] = self._calculate_1h_bias(candles_1h, bias_result['4h'])
        
        # 15m Bias (Entry Timing)
        bias_result['15m'] = self._calculate_15m_bias(candles_15m, bias_result['1h'])
        
        # Cache for this symbol
        self.bias_cache[symbol] = bias_result.copy()
        
        return bias_result
    
    def _calculate_4h_bias(self, candles: list) -> MarketBias:
        """Calculate primary trend bias from 4h candles"""
        if len(candles) < 20:
            return MarketBias.NEUTRAL
            
        closes = [float(c['close']) for c in candles[-20:]]
        highs = [float(c['high']) for c in candles[-20:]]
        lows = [float(c['low']) for c in candles[-20:]]
        
        # Check for Higher Highs / Higher Lows (BULL)
        hh_count = 0
        hl_count = 0
        lh_count = 0  
        ll_count = 0
        
        for i in range(5, len(closes)):
            if closes[i] > closes[i-5]:
                hh_count += 1
            if lows[i] > lows[i-5]:
                hl_count += 1
            if highs[i] < highs[i-5]:
                lh_count += 1
            if closes[i] < closes[i-5]:
                ll_count += 1
                
        # Simple trend determination
        if hh_count >= 3 and hl_count >= 3:
            return MarketBias.BULL
        elif ll_count >= 3 and lh_count >= 3:
            return MarketBias.BEAR
        else:
            return MarketBias.NEUTRAL
    
    def _calculate_1h_bias(self, candles: list, ht_bias: MarketBias) -> MarketBias:
        """Calculate intermediate bias considering HTF context"""
        if len(candles) < 15:
            return ht_bias
            
        closes = [float(c['close']) for c in candles[-15:]]
        
        # Simple moving average comparison
        ma_short = np.mean(closes[-5:])
        ma_long = np.mean(closes[-15:])
        
        if ht_bias == MarketBias.BULL and ma_short > ma_long:
            return MarketBias.BULL
        elif ht_bias == MarketBias.BEAR and ma_short < ma_long:
            return MarketBias.BEAR
        else:
            return MarketBias.NEUTRAL
    
    def _calculate_15m_bias(self, candles: list, mt_bias: MarketBias) -> MarketBias:
        """Calculate entry timing bias"""
        if len(candles) < 10:
            return mt_bias
            
        closes = [float(c['close']) for c in candles[-10:]]
        current_close = closes[-1]
        recent_high = max(closes[-5:])
        recent_low = min(closes[-5:])
        
        # Price action relative to recent range
        if mt_bias == MarketBias.BULL and current_close > recent_low + (recent_high - recent_low) * 0.5:
            return MarketBias.BULL
        elif mt_bias == MarketBias.BEAR and current_close < recent_high - (recent_high - recent_low) * 0.5:
            return MarketBias.BEAR
        else:
            return MarketBias.NEUTRAL
    
    def validate_setup_consistency(self, symbol: str, setup_direction: str, timeframe: str) -> Tuple[bool, str]:
        """
        Validate if setup is consistent with higher timeframe bias
        Returns (is_valid, reason)
        """
        if symbol not in self.bias_cache:
            return True, "No bias data available"
            
        bias_data = self.bias_cache[symbol]
        htf_bias = bias_data.get('4h', MarketBias.NEUTRAL)
        
        # Countertrend rules
        if htf_bias == MarketBias.BEAR and setup_direction == 'long':
            return False, "Countertrend: 4h BEAR but setup is LONG"
        elif htf_bias == MarketBias.BULL and setup_direction == 'short':
            return False, "Countertrend: 4h BULL but setup is SHORT"
            
        return True, "Consistent with HTF bias"

# Global instance
bias_resolver = BiasResolver()