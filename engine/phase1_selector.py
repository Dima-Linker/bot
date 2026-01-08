#!/usr/bin/env python3
"""
Phase 1 Selection System - Immediate Diversity Fix with Rotation
Applies symbol and topic caps without changing modules/scoring
Includes symbol rotation for better diversity over time
"""

from typing import List, Dict, Optional
from collections import defaultdict
import json

# Rotation policy (hours between same symbol in same topic)
ROTATION_POLICY = {
    'COMBO': 6,      # 6 hours
    'IDEA': 3,       # 3 hours  
    'FIBONACCI': 2,  # 2 hours
    'LIQUIDITY': 2,  # 2 hours
    'PUMP': 1        # 1 hour
}

class Phase1Selector:
    """Simple selector for immediate diversity improvement with rotation"""
    
    def __init__(self):
        # Phase 1 caps
        self.MAX_ALERTS_PER_SYMBOL_PER_SCAN = 1
        self.TOPIC_CAPS = {
            'COMBO': 5,
            'IDEA': 6, 
            'FIBONACCI': 10,
            'LIQUIDITY': 10,
            'PUMP': 6
        }
        self.GLOBAL_MAX = 20
    
    def extract_topic_from_decision(self, decision: Dict) -> str:
        """Extract correct topic from decision object"""
        signal_type = decision.get('type', '').upper()
        message_type = decision.get('message_type', '').upper()
        
        # Priority: explicit message type > signal type
        if 'TRADE' in message_type or signal_type == 'COMBO':
            return 'COMBO'
        elif 'WATCHLIST' in message_type or signal_type == 'IDEA':
            return 'IDEA'
        elif 'FIB' in signal_type:
            return 'FIBONACCI'
        elif 'SMC' in signal_type or 'LIQ' in signal_type:
            return 'LIQUIDITY'
        elif 'PUMP' in signal_type:
            return 'PUMP'
        else:
            # Fallback based on score
            score = decision.get('score_total', 0)
            return 'COMBO' if score >= 300 else 'IDEA'
    
    def select_signals_phase1(self, raw_decisions: List[Dict], repo=None, user_id: Optional[str] = None) -> List[Dict]:
        """
        Phase 1: Apply symbol and topic caps for immediate diversity
        With optional rotation checking if repo and user_id provided
        """
        if not raw_decisions:
            return []
        
        # Sort by score descending for best selection
        sorted_decisions = sorted(
            raw_decisions,
            key=lambda x: x.get('score_total', 0),
            reverse=True
        )
        
        # Track selections
        symbol_selected = set()
        topic_counts = defaultdict(int)
        selected_decisions = []
        rotation_skips = 0
        
        for decision in sorted_decisions:
            symbol = decision['symbol']
            topic = self.extract_topic_from_decision(decision)
            score = decision.get('score_total', 0)
            
            # Check rotation policy if repo is available
            if repo and user_id:
                rotation_hours = ROTATION_POLICY.get(topic, 2)
                if not repo.can_send_symbol(user_id, topic, symbol, rotation_hours):
                    print(f"[SELECTOR] Skipping {symbol} - rotation cooldown for {topic}")
                    rotation_skips += 1
                    continue
            
            # Apply symbol cap (max 1 per symbol)
            if symbol in symbol_selected:
                print(f"[SELECTOR] Skipping {symbol} - already selected")
                continue
            
            # Apply topic cap
            if topic_counts[topic] >= self.TOPIC_CAPS.get(topic, 10):
                print(f"[SELECTOR] Skipping {topic} - cap reached ({topic_counts[topic]})")
                continue
            
            # Apply global cap
            if len(selected_decisions) >= self.GLOBAL_MAX:
                print(f"[SELECTOR] Global cap reached ({self.GLOBAL_MAX})")
                break
            
            # Select this decision
            symbol_selected.add(symbol)
            topic_counts[topic] += 1
            selected_decisions.append(decision)
            
            # Update rotation tracking if repo available
            if repo and user_id:
                repo.set_last_sent(user_id, topic, symbol)
            
            print(f"[SELECTOR] SELECTED {symbol} {decision['timeframe']} -> {topic} (score: {score})")
        
        print(f"[SELECTOR] Final selection: {len(selected_decisions)} signals")
        print(f"[SELECTOR] By topic: {dict(topic_counts)}")
        if rotation_skips > 0:
            print(f"[SELECTOR] Rotation skips: {rotation_skips}")
        
        return selected_decisions

# Global selector instance
phase1_selector = Phase1Selector()

def get_phase1_selector() -> Phase1Selector:
    return phase1_selector

def apply_phase1_selection(raw_decisions: List[Dict]) -> List[Dict]:
    """Apply Phase 1 selection to raw decisions"""
    selector = get_phase1_selector()
    return selector.select_signals_phase1(raw_decisions)

__all__ = ['Phase1Selector', 'get_phase1_selector', 'apply_phase1_selection']