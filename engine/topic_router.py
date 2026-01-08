#!/usr/bin/env python3
"""
Hard Topic Router - Enforces strict topic separation
Prevents cross-topic signal leakage
"""

from typing import Dict, Optional
from enum import Enum

class TopicType(Enum):
    """Strict topic categorization"""
    FIBONACCI = "FIBONACCI"      # 📐 Only FIB ALERTS
    LIQUIDITY = "LIQUIDITY"      # 💧 Only SMC/Liquidity Alerts  
    IDEA = "IDEA"               # 🟡 Only Watchlist/IDEA Signals
    COMBO = "COMBO"             # 🧠 Only High-Quality/TRADE Signals
    PUMP = "PUMP"               # 🔥 Only Momentum/Pump Alerts
    GENERAL = "GENERAL"         # 📢 General Messages (fallback)

# Confirmed Telegram Forum Topic Thread IDs
TOPIC_THREAD_IDS: Dict[TopicType, int] = {
    TopicType.FIBONACCI: 9,      # 📐 FIBONACCI Topic
    TopicType.LIQUIDITY: 11,     # 💧 LIQUIDITY | SMC Topic  
    TopicType.IDEA: 114,         # 🟡 IDEA Topic
    TopicType.COMBO: 5,          # 🧠 COMBO | High-Quality Topic
    TopicType.PUMP: 15,          # 🔥 PUMP | MOMENTUM Topic
    TopicType.GENERAL: 1          # 📢 General Chat
}

def classify_signal(signal_text: str, signal_data: dict) -> TopicType:
    """
    Hard classification - no ambiguity allowed
    
    Rules:
    1. FIBONACCI: Must contain Fibonacci/Golden Ratio keywords
    2. LIQUIDITY: Must contain SMC/liquidity keywords  
    3. PUMP: Must contain pump/momentum/volume keywords
    4. COMBO: High scores (300+) with structural confirmation
    5. IDEA: Everything else goes to IDEA (safe fallback)
    """
    
    text_lower = signal_text.lower()
    
    # Priority 1: Explicit module identification
    if signal_data.get('module') == 'fibonacci':
        return TopicType.FIBONACCI
        
    if signal_data.get('module') == 'smc':
        return TopicType.LIQUIDITY
        
    if signal_data.get('module') == 'pump':
        return TopicType.PUMP
    
    # Priority 2: Content-based classification
    
    # HIGH-SCORE COMBO FIRST (prevent overlap with PUMP)
    score = signal_data.get('score', 0)
    if score >= 300:
        # Check for high-quality structural keywords first
        combo_keywords = [
            'combo', 'structure', 'confirmation', 
            'choch', 'break and close', 'lh/hl'
        ]
        if any(keyword in text_lower for keyword in combo_keywords):
            return TopicType.COMBO
    
    # FIBONACCI ALERTS (strict)
    if any(keyword in text_lower for keyword in [
        'fibonacci', 'fib', 'golden ratio', 'retracement', 
        'extension', '0.618', '0.786', 'fib level'
    ]):
        return TopicType.FIBONACCI
    
    # LIQUIDITY ALERTS (strict)  
    if any(keyword in text_lower for keyword in [
        'liquidity', 'smc', 'stop hunt', 'liquidity sweep',
        'equal high', 'equal low', 'eqh', 'eql'
    ]):
        return TopicType.LIQUIDITY
    
    # PUMP ALERTS (strict - only for lower scores or non-combo)
    if any(keyword in text_lower for keyword in [
        'pump', 'momentum', 'volume spike', 
        'acceleration', 'strength'
    ]):
        return TopicType.PUMP
    
    # Default fallback - IDEA (Watchlist)
    return TopicType.IDEA

def get_thread_id(topic_type: TopicType) -> int:
    """Get the Telegram thread ID for a topic type"""
    return TOPIC_THREAD_IDS.get(topic_type, TOPIC_THREAD_IDS[TopicType.GENERAL])

def route_message(signal_text: str, signal_data: dict) -> tuple[TopicType, int]:
    """
    Route message to correct topic
    Returns (topic_type, thread_id)
    """
    topic_type = classify_signal(signal_text, signal_data)
    thread_id = get_thread_id(topic_type)
    return topic_type, thread_id

# Export for use in other modules
__all__ = ['TopicType', 'classify_signal', 'get_thread_id', 'route_message']