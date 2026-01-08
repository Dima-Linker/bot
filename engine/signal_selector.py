#!/usr/bin/env python3
"""
Professional Signal Selection Engine
Implements diversity controls, topic balancing, and two-tier system
"""

from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

class SignalPriority(Enum):
    """Signal priority levels for selection"""
    COMBO = 100      # Highest priority
    TRADE = 90       # High priority  
    IDEA = 70        # Medium priority
    FIBONACCI = 50   # Module alerts
    LIQUIDITY = 50   # Module alerts
    PUMP = 60        # Module alerts

class TopicType(Enum):
    """Telegram topic types"""
    COMBO = "COMBO"
    IDEA = "IDEA" 
    FIBONACCI = "FIBONACCI"
    LIQUIDITY = "LIQUIDITY"
    PUMP = "PUMP"

@dataclass
class CandidateSignal:
    """Normalized candidate signal for selection"""
    symbol: str
    timeframe: str
    signal_type: str  # combo, idea, fib_alert, etc.
    message_type: str  # WATCHLIST, TRADE_FREIGABE
    score: int
    side: str
    levels: Dict  # Contains zone data, fib levels, etc.
    reasons: List[str]
    setup_id: Optional[str]
    priority: int
    topic: TopicType
    dedup_key_components: Dict  # For fine deduplication

class SignalSelector:
    """Professional signal selection engine with diversity controls"""
    
    def __init__(self):
        # Diversity limits
        self.MAX_ALERTS_PER_SYMBOL_PER_SCAN = 1
        self.MAX_ALERTS_PER_SCAN = 15
        self.TOPIC_CAPS = {
            TopicType.COMBO: 3,
            TopicType.IDEA: 4,
            TopicType.FIBONACCI: 3,
            TopicType.LIQUIDITY: 3,
            TopicType.PUMP: 3
        }
    
    def normalize_candidates(self, raw_decisions: List[Dict]) -> List[CandidateSignal]:
        """Convert raw decisions to normalized candidates with priorities"""
        candidates = []
        
        for decision in raw_decisions:
            # Determine topic and priority
            topic, priority = self._determine_topic_and_priority(decision)
            
            # Create dedup key components
            dedup_components = self._create_dedup_components(decision)
            
            candidate = CandidateSignal(
                symbol=decision['symbol'],
                timeframe=decision['timeframe'],
                signal_type=decision['type'],
                message_type=decision.get('message_type', ''),
                score=decision.get('score_total', 0),
                side=decision.get('side', ''),
                levels=decision.get('levels', {}),
                reasons=decision.get('reasons', []),
                setup_id=decision.get('setup_id'),
                priority=priority,
                topic=topic,
                dedup_key_components=dedup_components
            )
            candidates.append(candidate)
        
        return candidates
    
    def _determine_topic_and_priority(self, decision: Dict) -> Tuple[TopicType, int]:
        """Determine correct topic and priority for signal"""
        signal_type = decision['type']
        message_type = decision.get('message_type', '')
        
        # Priority mapping
        if signal_type == 'combo':
            return TopicType.COMBO, SignalPriority.COMBO.value
        elif message_type == 'TRADE_FREIGABE':
            return TopicType.COMBO, SignalPriority.TRADE.value
        elif message_type == 'WATCHLIST' or signal_type == 'idea':
            return TopicType.IDEA, SignalPriority.IDEA.value
        elif signal_type == 'fib_alert':
            return TopicType.FIBONACCI, SignalPriority.FIBONACCI.value
        elif signal_type == 'smc_alert':
            return TopicType.LIQUIDITY, SignalPriority.LIQUIDITY.value
        elif signal_type == 'pump_alert':
            return TopicType.PUMP, SignalPriority.PUMP.value
        else:
            # Fallback - determine by score
            score = decision.get('score_total', 0)
            if score >= 300:
                return TopicType.COMBO, SignalPriority.COMBO.value
            else:
                return TopicType.IDEA, SignalPriority.IDEA.value
    
    def _create_dedup_components(self, decision: Dict) -> Dict:
        """Create fine-grained deduplication components"""
        levels = decision.get('levels', {})
        
        # Extract key level information for dedup
        setup_anchor = None
        zone_low = None
        zone_high = None
        
        # Fibonacci levels
        if 'fibo_618' in levels:
            setup_anchor = levels['fibo_618']
        elif 'fibo_786' in levels:
            setup_anchor = levels['fibo_786']
        
        # SMC levels
        if 'zone_low' in levels and 'zone_high' in levels:
            zone_low = levels['zone_low']
            zone_high = levels['zone_high']
            if not setup_anchor:
                setup_anchor = (zone_low + zone_high) / 2
        
        # Round for deduplication tolerance
        def safe_round(value, decimals=2):
            return round(value, decimals) if value is not None else None
        
        return {
            'setup_anchor_level': safe_round(setup_anchor, 4),
            'zone_low': safe_round(zone_low, 4),
            'zone_high': safe_round(zone_high, 4),
            'side': decision.get('side', ''),
            'score_group': decision.get('score_total', 0) // 50  # Group by 50-point ranges
        }
    
    def select_signals(self, candidates: List[CandidateSignal]) -> Tuple[List[CandidateSignal], List[CandidateSignal]]:
        """
        Main selection algorithm
        Returns: (selected_elite, remaining_good_for_summary)
        """
        if not candidates:
            return [], []
        
        # Step 1: Sort by priority and score
        sorted_candidates = sorted(
            candidates, 
            key=lambda x: (x.priority, x.score), 
            reverse=True
        )
        
        # Step 2: Apply symbol diversity (max 1 per symbol)
        symbol_selected = {}
        by_topic = defaultdict(list)
        
        for candidate in sorted_candidates:
            # Skip if symbol already has alert in this scan
            if candidate.symbol in symbol_selected:
                continue
                
            # Check topic cap
            topic_count = len(by_topic[candidate.topic])
            if topic_count >= self.TOPIC_CAPS[candidate.topic]:
                continue
            
            # Add to selected
            symbol_selected[candidate.symbol] = candidate
            by_topic[candidate.topic].append(candidate)
        
        # Step 3: Apply global cap
        all_selected = []
        for topic_candidates in by_topic.values():
            all_selected.extend(topic_candidates)
        
        # Sort by priority for final selection
        all_selected.sort(key=lambda x: (x.priority, x.score), reverse=True)
        elite_signals = all_selected[:self.MAX_ALERTS_PER_SCAN]
        
        # Step 4: Identify remaining good candidates for summary
        selected_symbols = {s.symbol for s in elite_signals}
        remaining_good = [
            c for c in candidates 
            if c.symbol not in selected_symbols and c.score >= 200
        ]
        
        # Sort remaining by score
        remaining_good.sort(key=lambda x: x.score, reverse=True)
        
        return elite_signals, remaining_good
    
    def create_summary_message(self, good_candidates: List[CandidateSignal], max_items: int = 15) -> str:
        """Create market radar summary for good setups"""
        if not good_candidates:
            return ""
        
        summary = "📡 Market Radar - Good Setups\n"
        summary += f"Found {len(good_candidates)} additional opportunities:\n\n"
        
        # Group by topic
        by_topic = defaultdict(list)
        for candidate in good_candidates[:max_items]:
            by_topic[candidate.topic].append(candidate)
        
        for topic, candidates in by_topic.items():
            if candidates:
                summary += f"**{topic.value}**:\n"
                for cand in candidates[:3]:  # Max 3 per topic
                    side_icon = "🟢" if cand.side == 'long' else "🔴" if cand.side == 'short' else "⚪"
                    summary += f"• {cand.symbol} ({cand.timeframe}) {side_icon} {cand.score} pts\n"
                summary += "\n"
        
        return summary

# Global selector instance
selector = SignalSelector()

def get_signal_selector() -> SignalSelector:
    """Get global signal selector instance"""
    return selector

__all__ = ['SignalSelector', 'CandidateSignal', 'get_signal_selector', 'TopicType', 'SignalPriority']