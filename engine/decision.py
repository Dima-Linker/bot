from typing import List, Dict, Optional, Literal
from dataclasses import dataclass, field
import hashlib
import time

from .types import FeatureResult

# Existing Direction and Strength types
Direction = Literal['long', 'short', 'both']
Strength = Literal['weak', 'medium', 'strong', 'elite']

@dataclass
class SetupResult:
    """Result of IDEA vs TRADE evaluation"""
    status: Literal['NONE', 'IDEA', 'TRADE']
    symbol: str
    timeframe: str
    side: Direction
    idea_score: Optional[int] = None
    trade_score: Optional[int] = None
    reasons: List[str] = field(default_factory=list)
    levels: Optional[Dict] = None
    setup_id: Optional[str] = None

def evaluate_idea_trigger(features: List[FeatureResult]) -> Optional[SetupResult]:
    """
    Evaluate if conditions for IDEA (Watchlist) are met
    Requires at least 2 conditions:
    1. Liquidity Grab (Sweep + Reclaim)
    2. Fib Zone hit (Golden Zone 0.618-0.786)
    Optional: Confluence factors
    """
    if not features:
        return None
    
    liquidity_found = False
    fib_found = False
    confluence_score = 0
    reasons = []
    levels = {}
    
    # Check for liquidity grab patterns
    for feature in features:
        if feature.module == 'smc' and feature.levels:
            # Look for sweep patterns
            if 'sweep_high' in feature.levels or 'sweep_low' in feature.levels:
                if feature.levels.get('reclaim_close', False):
                    liquidity_found = True
                    reasons.append("Liquidity Grab mit Reclaim erkannt")
                    levels.update({
                        'sweep_level': feature.levels.get('sweep_high') or feature.levels.get('sweep_low'),
                        'reclaim_confirmed': True
                    })
    
    # Check for Fibonacci zone hits
    for feature in features:
        if feature.module == 'fibonacci' and feature.levels:
            # Check for golden zone hits (0.618-0.786)
            fib_hit = feature.levels.get('fib_hit_ratio', 0)
            if 0.618 <= fib_hit <= 0.786:
                fib_found = True
                reasons.append(f"Fibonacci Golden Zone getroffen ({fib_hit:.3f})")
                levels.update({
                    'fib_zone_low': feature.levels.get('zone_low'),
                    'fib_zone_high': feature.levels.get('zone_high'),
                    'fib_hit_price': feature.levels.get('hit_price')
                })
    
    # Check for confluence (additional confirmation)
    for feature in features:
        if feature.module in ['volume', 'rsi_divergence', 'macd']:
            if feature.score >= 70:  # Strong signal
                confluence_score += 20
                reasons.append(f"{feature.module.title()} bestätigt Setup ({feature.score})")
    
    # Calculate IDEA score
    idea_score = 0
    if liquidity_found:
        idea_score += 50
    if fib_found:
        idea_score += 40
    idea_score += min(confluence_score, 30)  # Cap confluence at 30 points
    
    # IDEA triggered if score >= 80 (requires at least 2 main conditions)
    if idea_score >= 80 and (liquidity_found or fib_found):
        # Determine side from features
        side = 'both'
        for feature in features:
            if feature.direction in ['long', 'short']:
                side = feature.direction
                break
        
        return SetupResult(
            status='IDEA',
            symbol=features[0].symbol,
            timeframe=features[0].timeframe,
            side=side,
            idea_score=idea_score,
            reasons=reasons,
            levels=levels
        )
    
    return None

def evaluate_trade_confirmation(
    features: List[FeatureResult], 
    existing_idea: Optional[Dict] = None
) -> Optional[SetupResult]:
    """
    Evaluate if IDEA should be upgraded to TRADE
    Requires at least 1 confirmation:
    1. CHoCH (Close confirmed structure break)
    2. Break & Close under/over key level
    3. LH+Break / HL+Break after sweep
    """
    if not features:
        return None
    
    confirmation_found = False
    reasons = []
    levels = {}
    trade_score_bonus = 0
    
    # Check for CHoCH (Change of Character)
    for feature in features:
        if feature.module == 'smc' and feature.levels:
            if feature.levels.get('choch_confirmed', False):
                confirmation_found = True
                trade_score_bonus += 40
                reasons.append("CHoCH bestätigt (Structure Break mit Close)")
                levels['choch_level'] = feature.levels.get('broken_level')
    
    # Check for Break & Close
    for feature in features:
        if feature.module in ['smc', 'fibonacci'] and feature.levels:
            if feature.levels.get('break_and_close', False):
                confirmation_found = True
                trade_score_bonus += 35
                reasons.append("Break & Close bestätigt")
                levels['break_level'] = feature.levels.get('break_level')
    
    # Check for LH+Break / HL+Break
    for feature in features:
        if feature.module == 'smc' and feature.levels:
            if feature.levels.get('lh_break', False) or feature.levels.get('hl_break', False):
                confirmation_found = True
                trade_score_bonus += 30
                break_type = "LH+Break" if feature.levels.get('lh_break') else "HL+Break"
                reasons.append(f"{break_type} nach Sweep bestätigt")
                levels['structure_break'] = feature.levels.get('structure_level')
    
    if confirmation_found and existing_idea:
        # Upgrade existing IDEA to TRADE
        base_score = existing_idea.get('idea_score', 0)
        trade_score = min(base_score + trade_score_bonus, 150)  # Cap at 150
        
        return SetupResult(
            status='TRADE',
            symbol=existing_idea['symbol'],
            timeframe=existing_idea['timeframe'],
            side=existing_idea['side'],
            idea_score=existing_idea.get('idea_score'),
            trade_score=trade_score,
            reasons=reasons,
            levels={**existing_idea.get('levels', {}), **levels},
            setup_id=existing_idea['setup_id']
        )
    elif confirmation_found and not existing_idea:
        # Direct TRADE signal (aggressive mode)
        return SetupResult(
            status='TRADE',
            symbol=features[0].symbol,
            timeframe=features[0].timeframe,
            side=features[0].direction,
            trade_score=100 + trade_score_bonus,
            reasons=reasons,
            levels=levels
        )
    
    return None

def decide_signal_with_states(
    features: List[FeatureResult], 
    min_score: int,
    repo,  # Database repo instance
    user_id: str,
    preset_mode: str = 'normal'  # conservative, normal, aggressive
) -> Optional[Dict]:
    """
    Enhanced decision engine with IDEA vs TRADE states
    """
    if not features:
        return None
    
    symbol = features[0].symbol
    timeframe = features[0].timeframe
    
    # Check for existing IDEA first
    existing_idea = repo.get_existing_idea(user_id, symbol, timeframe)
    
    # Evaluate for TRADE confirmation first (upgrade existing IDEA)
    trade_result = evaluate_trade_confirmation(features, existing_idea)
    if trade_result:
        if existing_idea:
            # Upgrade existing IDEA to TRADE
            success = repo.upgrade_setup_to_trade(trade_result.setup_id, trade_result.trade_score)
            if success:
                return {
                    'type': 'trade_upgrade',
                    'status': 'TRADE',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'side': trade_result.side,
                    'score_total': trade_result.trade_score,
                    'reasons': trade_result.reasons,
                    'levels': trade_result.levels,
                    'setup_id': trade_result.setup_id,
                    'message_type': 'TRADE_FREIGABE'
                }
        else:
            # Direct TRADE signal (aggressive mode)
            if preset_mode == 'aggressive':
                # Convert direction to database format (long/short -> bullish/bearish)
                db_side = 'bullish' if trade_result.side == 'long' else 'bearish'
                
                setup_id = repo.save_active_setup(
                    user_id=user_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    side=db_side,
                    status='TRADE',
                    trade_score=trade_result.trade_score,
                    levels=trade_result.levels
                )
                return {
                    'type': 'direct_trade',
                    'status': 'TRADE',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'side': trade_result.side,
                    'score_total': trade_result.trade_score,
                    'reasons': trade_result.reasons,
                    'levels': trade_result.levels,
                    'setup_id': setup_id,
                    'message_type': 'TRADE_FREIGABE'
                }
    
    # If no TRADE confirmation, check for new IDEA
    if not existing_idea:
        idea_result = evaluate_idea_trigger(features)
        if idea_result and idea_result.idea_score is not None and idea_result.idea_score >= min_score:
            # Save new IDEA based on preset mode
            should_save_idea = True
            if preset_mode == 'conservative':
                should_save_idea = False  # Conservative mode doesn't save ideas
            elif preset_mode == 'normal':
                should_save_idea = idea_result.idea_score >= 90  # Higher threshold
            
            if should_save_idea:
                # Convert direction to database format (long/short -> bullish/bearish)
                db_side = 'bullish' if idea_result.side == 'long' else 'bearish'
                
                setup_id = repo.save_active_setup(
                    user_id=user_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    side=db_side,
                    status='IDEA',
                    idea_score=idea_result.idea_score,
                    levels=idea_result.levels
                )
                
                return {
                    'type': 'idea_detected',
                    'status': 'IDEA',
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'side': idea_result.side,
                    'score_total': idea_result.idea_score,
                    'reasons': idea_result.reasons,
                    'levels': idea_result.levels,
                    'setup_id': setup_id,
                    'message_type': 'WATCHLIST'
                }
    
    # Fall back to traditional scoring if no state logic applies
    return decide_signal(features, min_score)

# Keep existing decide_signal function for backward compatibility
def decide_signal(features: List[FeatureResult], min_score: int) -> Optional[Dict]:
    """
    Original decision logic - kept for compatibility
    """
    if not features:
        return None
    
    # Combine scores with category requirements
    total = sum(min(f.score, 100) for f in features)  # Clamp individual scores
    total = min(400, total)  # Cap total score
    
    # Require at least 2 categories for combo signals
    cats = set()
    for f in features:
        if f.module in ['fibonacci', 'smc']:
            cats.add('level')
        elif f.module in ['rsi_divergence', 'macd']:
            cats.add('momentum')
        elif f.module == 'volume':
            cats.add('participation')
    
    if total >= min_score and len(cats) >= 2:
        # Determine primary direction
        directions = [f.direction for f in features if f.direction in ['long', 'short']]
        primary_direction = directions[0] if directions else 'both'
        
        return {
            'type': 'combo',
            'symbol': features[0].symbol,
            'timeframe': features[0].timeframe,
            'side': primary_direction,
            'score_total': total,
            'features': features,
            'reasons': [r for f in features for r in f.reasons],
            'levels': features[0].levels if features else None
        }
    
    return None