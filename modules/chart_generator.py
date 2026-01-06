"""
Chart Generation Module for the Crypto-Signal Hub-Bot
Generates TradingView-style charts with signal indicators
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime
import os
from typing import Dict, List, Optional

from engine.types import FeatureResult


def create_tradingview_chart(df: pd.DataFrame, symbol: str, timeframe: str, 
                           signal_info: Optional[Dict] = None) -> str:
    """
    Create a TradingView-style chart with technical indicators
    Returns the file path of the generated chart
    """
    # Create figure with multiple subplots
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), 
                                         gridspec_kw={'height_ratios': [3, 1, 1]})
    fig.patch.set_facecolor('#1e1e1e')  # Dark background
    
    # Main price chart
    ax1.set_facecolor('#1e1e1e')
    ax1.plot(df.index, df['close'], color='#00ff88', linewidth=1.5, label='Close')
    
    # Add moving averages
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma50'] = df['close'].rolling(window=50).mean()
    ax1.plot(df.index, df['ma20'], color='#ff8800', linewidth=1, label='MA20', alpha=0.7)
    ax1.plot(df.index, df['ma50'], color='#8888ff', linewidth=1, label='MA50', alpha=0.7)
    
    # Add volume bars
    colors = ['#00ff88' if close > open else '#ff4444' 
              for close, open in zip(df['close'], df['open'])]
    ax2.set_facecolor('#1e1e1e')
    ax2.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('Volume', color='white')
    
    # Add RSI
    rsi = calculate_rsi(df['close'])
    ax3.set_facecolor('#1e1e1e')
    ax3.plot(df.index, rsi, color='#ff00ff', linewidth=1, label='RSI')
    ax3.axhline(y=70, color='#ff4444', linestyle='--', alpha=0.5)
    ax3.axhline(y=30, color='#00ff88', linestyle='--', alpha=0.5)
    ax3.set_ylabel('RSI', color='white')
    ax3.set_ylim(0, 100)
    
    # Add signal markers if provided
    if signal_info:
        signal_type = signal_info.get('type', '')
        signal_strength = signal_info.get('strength', 'medium')
        
        # Different colors based on signal type and strength
        color_map = {
            'strong': '#ff8800',
            'elite': '#ff00ff',
            'medium': '#ffff00',
            'weak': '#888888'
        }
        
        signal_color = color_map.get(signal_strength, '#ffffff')
        
        # Add a vertical line at the latest candle
        latest_idx = df.index[-1]
        ax1.axvline(x=latest_idx, color=signal_color, linestyle='-', alpha=0.7, linewidth=2)
        
        # Add signal annotation
        ax1.annotate(f'{signal_type}', 
                    xy=(latest_idx, df['close'].iloc[-1]),
                    xytext=(latest_idx, df['close'].iloc[-1] * 1.02),
                    color=signal_color,
                    fontsize=10,
                    ha='center',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='#333333', alpha=0.7, edgecolor=signal_color))
    
    # Formatting
    ax1.set_title(f'{symbol} - {timeframe}', color='white', fontsize=14)
    ax1.grid(True, alpha=0.3, color='#444444')
    ax1.tick_params(colors='white')
    ax2.tick_params(colors='white')
    ax3.tick_params(colors='white')
    
    # Add legend
    ax1.legend(loc='upper left', frameon=False, labelcolor='white')
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, color='white')
    
    # Adjust layout
    plt.tight_layout()
    
    # Create filename with timestamp
    timestamp = int(datetime.now().timestamp())
    chart_filename = f"chart_{symbol}_{timeframe}_{timestamp}.png"
    chart_path = os.path.join('data', 'charts', chart_filename)
    
    # Ensure the charts directory exists
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    
    # Save the chart
    plt.savefig(chart_path, facecolor='#1e1e1e', dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return pd.Series(rsi)


def add_fibonacci_levels(ax, df: pd.DataFrame):
    """Add Fibonacci retracement levels to the chart"""
    # Calculate swing high and low for the recent period
    recent_high = df['high'].rolling(window=20).max().iloc[-1]
    recent_low = df['low'].rolling(window=20).min().iloc[-1]
    
    if pd.isna(recent_high) or pd.isna(recent_low):
        return
    
    price_range = recent_high - recent_low
    
    # Fibonacci levels
    fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
    
    for level in fib_levels:
        fib_price = recent_low + (price_range * level)
        ax.axhline(y=fib_price, color='#888888', linestyle=':', alpha=0.6, linewidth=0.8)
        ax.text(df.index[-len(df)//4], fib_price, f'{level:.3f}', 
               color='#888888', fontsize=8, alpha=0.7)


def generate_signal_chart(df: pd.DataFrame, symbol: str, timeframe: str, 
                        feature_results: List[FeatureResult]) -> str:
    """
    Generate a chart specifically for a signal with relevant indicators
    """
    # Create figure with multiple subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                   gridspec_kw={'height_ratios': [3, 1]})
    fig.patch.set_facecolor('#1e1e1e')  # Dark background
    
    # Main price chart
    ax1.set_facecolor('#1e1e1e')
    ax1.plot(df.index, df['close'], color='#00ff88', linewidth=2, label='Close')
    ax1.plot(df.index, df['high'], color='#888888', linewidth=0.5, alpha=0.5)
    ax1.plot(df.index, df['low'], color='#888888', linewidth=0.5, alpha=0.5)
    
    # Add moving averages
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma50'] = df['close'].rolling(window=50).mean()
    ax1.plot(df.index, df['ma20'], color='#ff8800', linewidth=1, label='MA20', alpha=0.7)
    ax1.plot(df.index, df['ma50'], color='#8888ff', linewidth=1, label='MA50', alpha=0.7)
    
    # Add Fibonacci levels
    add_fibonacci_levels(ax1, df)
    
    # Add volume bars
    colors = ['#00ff88' if close > open else '#ff4444' 
              for close, open in zip(df['close'], df['open'])]
    ax2.set_facecolor('#1e1e1e')
    ax2.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.8)
    ax2.set_ylabel('Volume', color='white')
    
    # Add signal markers based on feature results
    for result in feature_results:
        if hasattr(result, 'candle_ts'):
            # For now, we'll add a marker at the latest candle
            # In a real implementation, we'd map the timestamp to the index
            latest_idx = df.index[-1]
            ax1.axvline(x=latest_idx, color='#ff00ff', linestyle='-', alpha=0.8, linewidth=2)
    
    # Formatting
    ax1.set_title(f'{symbol} - {timeframe} | Signal Chart', color='white', fontsize=14)
    ax1.grid(True, alpha=0.3, color='#444444')
    ax1.tick_params(colors='white')
    ax2.tick_params(colors='white')
    
    # Add legend
    ax1.legend(loc='upper left', frameon=False, labelcolor='white')
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, color='white')
    
    # Adjust layout
    plt.tight_layout()
    
    # Create filename with timestamp
    timestamp = int(datetime.now().timestamp())
    chart_filename = f"signal_chart_{symbol}_{timeframe}_{timestamp}.png"
    chart_path = os.path.join('data', 'charts', chart_filename)
    
    # Ensure the charts directory exists
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    
    # Save the chart
    plt.savefig(chart_path, facecolor='#1e1e1e', dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path


def create_chart_with_indicators(df: pd.DataFrame, symbol: str, timeframe: str, 
                               indicators: List[str] = None) -> str:
    """
    Create a chart with customizable indicators
    """
    if indicators is None:
        indicators = ['volume', 'rsi', 'ma']
    
    # Create figure
    fig, axes = plt.subplots(len(indicators) + 1, 1, figsize=(14, 12), 
                            gridspec_kw={'height_ratios': [3] + [1] * len(indicators)})
    fig.patch.set_facecolor('#1e1e1e')  # Dark background
    
    if len(indicators) == 0:
        axes = [axes]
    
    # Main price chart
    main_ax = axes[0]
    main_ax.set_facecolor('#1e1e1e')
    main_ax.plot(df.index, df['close'], color='#00ff88', linewidth=2, label='Close')
    
    # Add moving averages if requested
    if 'ma' in indicators:
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma50'] = df['close'].rolling(window=50).mean()
        main_ax.plot(df.index, df['ma20'], color='#ff8800', linewidth=1, label='MA20', alpha=0.7)
        main_ax.plot(df.index, df['ma50'], color='#8888ff', linewidth=1, label='MA50', alpha=0.7)
    
    # Add additional indicators based on the list
    for i, indicator in enumerate(indicators[1:], 1):
        if indicator == 'volume' and i < len(axes):
            ind_ax = axes[i]
            ind_ax.set_facecolor('#1e1e1e')
            colors = ['#00ff88' if close > open else '#ff4444' 
                      for close, open in zip(df['close'], df['open'])]
            ind_ax.bar(df.index, df['volume'], color=colors, alpha=0.6, width=0.8)
            ind_ax.set_ylabel('Volume', color='white')
        elif indicator == 'rsi' and i < len(axes):
            ind_ax = axes[i]
            ind_ax.set_facecolor('#1e1e1e')
            rsi = calculate_rsi(df['close'])
            ind_ax.plot(df.index, rsi, color='#ff00ff', linewidth=1, label='RSI')
            ind_ax.axhline(y=70, color='#ff4444', linestyle='--', alpha=0.5)
            ind_ax.axhline(y=30, color='#00ff88', linestyle='--', alpha=0.5)
            ind_ax.set_ylabel('RSI', color='white')
            ind_ax.set_ylim(0, 100)
    
    # Formatting
    main_ax.set_title(f'{symbol} - {timeframe} | Technical Analysis', color='white', fontsize=14)
    main_ax.grid(True, alpha=0.3, color='#444444')
    main_ax.tick_params(colors='white')
    
    for i in range(1, len(axes)):
        axes[i].tick_params(colors='white')
    
    # Add legend
    main_ax.legend(loc='upper left', frameon=False, labelcolor='white')
    
    # Rotate x-axis labels
    plt.xticks(rotation=45, color='white')
    
    # Adjust layout
    plt.tight_layout()
    
    # Create filename with timestamp
    timestamp = int(datetime.now().timestamp())
    chart_filename = f"technical_chart_{symbol}_{timeframe}_{timestamp}.png"
    chart_path = os.path.join('data', 'charts', chart_filename)
    
    # Ensure the charts directory exists
    os.makedirs(os.path.dirname(chart_path), exist_ok=True)
    
    # Save the chart
    plt.savefig(chart_path, facecolor='#1e1e1e', dpi=150, bbox_inches='tight')
    plt.close()
    
    return chart_path