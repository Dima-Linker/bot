# IDEA vs TRADE Implementation

## Summary
The Crypto-Signal Hub-Bot has been successfully enhanced with IDEA vs TRADE functionality. This separates location (IDEA) from timing (TRADE) for more professional and less noisy signals.

## Key Changes

### 1. Database Schema
- Added `active_setups` table to track IDEA/TRADE states
- Supports per-symbol/timeframe setup tracking
- Includes expiration and invalidation mechanisms

### 2. Decision Engine
- IDEA detection: Liquidity Grab + Fibonacci Golden Zone (0.618-0.786)
- TRADE confirmation: CHoCH, Break & Close, LH/HL Break patterns
- State-based decision making with preset support

### 3. Message System
- WATCHLIST messages for IDEA setups (yellow emoji)
- TRADE FREIGABE messages for confirmed entries (green/red emoji)
- Professional German formatting with proper risk guidance

### 4. Preset Support
- Conservative: TRADE only
- Normal: High-threshold IDEA + normal TRADE
- Aggressive: Lower thresholds for both

## Benefits
- Less noisy signals
- Better timing confirmation
- Professional multi-tier approach
- Improved risk management
- Flexible user preferences