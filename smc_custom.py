"""
Custom Smart Money Concepts Implementation
Eigene Implementierung von Order Blocks, Fair Value Gaps und anderen Smart Money Konzepten
"""

import pandas as pd
import numpy as np

def fibonacci(df, period=200):
    """
    Berechnet Fibonacci-Level basierend auf dem höchsten und niedrigsten Punkt in einem bestimmten Zeitraum
    """
    high = df['high'].tail(period).max()
    low = df['low'].tail(period).min()
    diff = high - low
    
    levels = {
        '0.0': low,
        '0.236': low + diff * 0.236,
        '0.382': low + diff * 0.382,
        '0.5': low + diff * 0.5,
        '0.618': low + diff * 0.618,
        '0.786': low + diff * 0.786,
        '1.0': high
    }
    return levels

def order_blocks(df, lookback=50, tolerance=0.002):
    """
    Erkennt potenzielle Order Blocks (Widerstands- und Unterstützungsareale)
    """
    # Finde signifikante Hochs und Tiefs
    highs = df['high'].rolling(window=lookback, center=True).max()
    lows = df['low'].rolling(window=lookback, center=True).min()
    
    # Erkenne Bereiche, wo Preise wiederholt Widerstand/Unterstützung fanden
    resistance_levels = []
    support_levels = []
    
    for i in range(lookback, len(df) - lookback):
        current_high = df['high'].iloc[i]
        current_low = df['low'].iloc[i]
        
        # Prüfe, ob das aktuelle Hoch ein signifikantes Hoch ist
        if abs(current_high - highs.iloc[i]) < df['close'].iloc[i] * tolerance:
            # Prüfe, ob es mehrere Berührungen gab (zeigt Stärke)
            nearby_highs = df['high'].iloc[i-lookback//2:i+lookback//2]
            touches = sum(abs(nearby_highs - current_high) < df['close'].iloc[i] * tolerance)
            if touches >= 2:
                resistance_levels.append({
                    'index': i,
                    'price': current_high,
                    'type': 'resistance',
                    'touches': touches
                })
        
        # Prüfe, ob das aktuelle Tief ein signifikantes Tief ist
        if abs(current_low - lows.iloc[i]) < df['close'].iloc[i] * tolerance:
            # Prüfe, ob es mehrere Berührungen gab (zeigt Stärke)
            nearby_lows = df['low'].iloc[i-lookback//2:i+lookback//2]
            touches = sum(abs(nearby_lows - current_low) < df['close'].iloc[i] * tolerance)
            if touches >= 2:
                support_levels.append({
                    'index': i,
                    'price': current_low,
                    'type': 'support',
                    'touches': touches
                })
    
    return {
        'resistance': pd.DataFrame(resistance_levels) if resistance_levels else pd.DataFrame(),
        'support': pd.DataFrame(support_levels) if support_levels else pd.DataFrame()
    }

def fair_value_gaps(df, lookback=10, tolerance=0.001):
    """
    Erkennt Fair Value Gaps - Bereiche ohne ausreichende Preishistorie
    """
    fvg_up = []  # Bullische FVGs (Preis hat Gap nach oben gemacht)
    fvg_down = []  # Bärische FVGs (Preis hat Gap nach unten gemacht)
    
    for i in range(lookback, len(df) - 1):
        # Bullischer FVG: Preis springt über vorheriges Hoch mit Gap
        if (df['low'].iloc[i] > df['high'].iloc[i-1] and 
            df['close'].iloc[i] > df['open'].iloc[i] and
            df['low'].iloc[i] - df['high'].iloc[i-1] > df['close'].iloc[i] * tolerance):
            
            fvg_up.append({
                'index': i,
                'bottom': df['high'].iloc[i-1],
                'top': df['low'].iloc[i],
                'type': 'bullish'
            })
        
        # Bärischer FVG: Preis springt unter vorheriges Tief mit Gap
        if (df['high'].iloc[i] < df['low'].iloc[i-1] and 
            df['close'].iloc[i] < df['open'].iloc[i] and
            df['low'].iloc[i-1] - df['high'].iloc[i] > df['close'].iloc[i] * tolerance):
            
            fvg_down.append({
                'index': i,
                'bottom': df['high'].iloc[i],
                'top': df['low'].iloc[i-1],
                'type': 'bearish'
            })
    
    return {
        'bullish': pd.DataFrame(fvg_up) if fvg_up else pd.DataFrame(),
        'bearish': pd.DataFrame(fvg_down) if fvg_down else pd.DataFrame()
    }

def break_of_structure(df, lookback=10):
    """
    Erkennt Break of Structure - Wann der Markt seine Struktur bricht
    """
    # Finde signifikante Hochs und Tiefs
    swing_highs = []
    swing_lows = []
    
    for i in range(lookback, len(df) - lookback):
        # Prüfe auf Swing High
        if (df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback].max()):
            swing_highs.append({
                'index': i,
                'price': df['high'].iloc[i],
                'type': 'high'
            })
        
        # Prüfe auf Swing Low
        if (df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback].min()):
            swing_lows.append({
                'index': i,
                'price': df['low'].iloc[i],
                'type': 'low'
            })
    
    # Erkenne Break of Structure (wenn ein Hoch gebrochen wird nach Abwärtstrend oder Tief nach Aufwärtstrend)
    bos_up = []  # Bullische BOS
    bos_down = []  # Bärische BOS
    
    for i in range(len(swing_highs)):
        if i > 0:
            # Bullische BOS: Wenn ein niedrigeres Hoch gebrochen wird
            if (swing_highs[i]['price'] > max([s['price'] for s in swing_highs[:i]]) and
                df['close'].iloc[swing_highs[i]['index']] > df['high'].iloc[swing_highs[i-1]['index']]):
                bos_up.append(swing_highs[i])
    
    for i in range(len(swing_lows)):
        if i > 0:
            # Bärische BOS: Wenn ein höheres Tief gebrochen wird
            if (swing_lows[i]['price'] < min([s['price'] for s in swing_lows[:i]]) and
                df['close'].iloc[swing_lows[i]['index']] < df['low'].iloc[swing_lows[i-1]['index']]):
                bos_down.append(swing_lows[i])
    
    return {
        'bullish': pd.DataFrame(bos_up) if bos_up else pd.DataFrame(),
        'bearish': pd.DataFrame(bos_down) if bos_down else pd.DataFrame()
    }