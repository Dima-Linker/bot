#!/usr/bin/env python3
"""
Simple Selection Wrapper for Scanner
"""

from typing import List, Dict
from engine.signal_selector import get_signal_selector

def apply_selection_filter(raw_decisions: List[Dict]) -> tuple[List[Dict], List[Dict]]:
    """
    Apply professional selection filtering to raw decisions
    Returns: (elite_signals_to_send, good_candidates_for_summary)
    """
    if not raw_decisions:
        return [], []
    
    # Get selector instance
    selector = get_signal_selector()
    
    # Normalize candidates
    candidates = selector.normalize_candidates(raw_decisions)
    
    # Apply selection algorithm
    elite_signals, good_candidates = selector.select_signals(candidates)
    
    # Convert back to decision format for sending
    elite_decisions = []
    for candidate in elite_signals:
        # Find original decision
        original_decision = next(
            (d for d in raw_decisions 
             if d['symbol'] == candidate.symbol and d['timeframe'] == candidate.timeframe),
            None
        )
        if original_decision:
            elite_decisions.append(original_decision)
    
    # Convert good candidates to simplified format for summary
    good_summaries = []
    for candidate in good_candidates[:15]:  # Limit for summary
        good_summaries.append({
            'symbol': candidate.symbol,
            'timeframe': candidate.timeframe,
            'score': candidate.score,
            'side': candidate.side,
            'topic': candidate.topic.value
        })
    
    print(f"[SELECTION] Converted {len(elite_signals)} elite signals, {len(good_candidates)} good candidates")
    
    return elite_decisions, good_summaries