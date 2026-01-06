CREATE TABLE IF NOT EXISTS user_settings (
  tg_user_id TEXT PRIMARY KEY,
  preset TEXT NOT NULL DEFAULT 'normal',
  modules_json TEXT NOT NULL DEFAULT '{}',
  watchlist_json TEXT NOT NULL DEFAULT '[]',
  combo_min_score INTEGER NOT NULL DEFAULT 70,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS signals_sent (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tg_user_id TEXT NOT NULL,
  dedup_key TEXT NOT NULL UNIQUE,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  candle_ts INTEGER NOT NULL,
  score_total INTEGER,
  payload_json TEXT NOT NULL,
  sent_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS cooldowns (
  tg_user_id TEXT NOT NULL,
  key TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  PRIMARY KEY (tg_user_id, key)
);

-- New table for IDEA vs TRADE state management
CREATE TABLE IF NOT EXISTS active_setups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    setup_id TEXT NOT NULL UNIQUE,  -- hash of symbol+timeframe+timestamp
    side TEXT NOT NULL CHECK(side IN ('bullish', 'bearish')),
    status TEXT NOT NULL CHECK(status IN ('IDEA', 'TRADE')),
    idea_score INTEGER,
    trade_score INTEGER,
    levels_json TEXT,  -- JSON with liquidity, fib, structure levels
    created_at INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    confirmed_at INTEGER,
    invalidated_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES user_settings(tg_user_id)
);

CREATE INDEX IF NOT EXISTS idx_active_setups_user_symbol_tf 
ON active_setups(user_id, symbol, timeframe);

CREATE INDEX IF NOT EXISTS idx_active_setups_status 
ON active_setups(status);

CREATE INDEX IF NOT EXISTS idx_active_setups_expires 
ON active_setups(expires_at);
