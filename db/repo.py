import json
import time
import hashlib
from typing import Optional, List, Dict, Any


class Repo:
    def __init__(self, conn):
        self.conn = conn

    # ---------- settings ----------
    def get_settings(self, tg_user_id: str) -> dict:
        cur = self.conn.execute('SELECT * FROM user_settings WHERE tg_user_id=?', (tg_user_id,))
        row = cur.fetchone()
        if not row:
            default = {
                'tg_user_id': tg_user_id,
                'preset': 'normal',
                'modules': {},
                'watchlist': [],
                'combo_min_score': 70,
            }
            self.save_settings(default)
            return default

        return {
            'tg_user_id': row['tg_user_id'],
            'preset': row['preset'],
            'modules': json.loads(row['modules_json']),
            'watchlist': json.loads(row['watchlist_json']),
            'combo_min_score': int(row['combo_min_score']),
        }

    def save_settings(self, settings: dict) -> None:
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO user_settings(tg_user_id,preset,modules_json,watchlist_json,combo_min_score,updated_at) "
            "VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(tg_user_id) DO UPDATE SET "
            "preset=excluded.preset, "
            "modules_json=excluded.modules_json, "
            "watchlist_json=excluded.watchlist_json, "
            "combo_min_score=excluded.combo_min_score, "
            "updated_at=excluded.updated_at",
            (
                settings['tg_user_id'],
                settings.get('preset', 'normal'),
                json.dumps(settings.get('modules', {})),
                json.dumps(settings.get('watchlist', [])),
                int(settings.get('combo_min_score', 70)),
                now,
            ),
        )
        self.conn.commit()

    # ---------- active setups ----------
    def create_setup_id(self, symbol: str, timeframe: str, timestamp: int) -> str:
        """Create unique setup ID hash"""
        data = f"{symbol}_{timeframe}_{timestamp}"
        return hashlib.md5(data.encode()).hexdigest()

    def save_active_setup(
        self,
        user_id: str,
        symbol: str,
        timeframe: str,
        side: str,
        status: str,
        idea_score: Optional[int] = None,
        trade_score: Optional[int] = None,
        levels: Optional[Dict[str, Any]] = None,
        expires_in_minutes: int = 120,  # 2 hours default
    ) -> str:
        """Save new active setup (IDEA or TRADE)"""
        setup_id = self.create_setup_id(symbol, timeframe, int(time.time()))
        now = int(time.time())
        expires_at = now + (expires_in_minutes * 60)
        
        levels_json = json.dumps(levels) if levels else None
        
        self.conn.execute(
            '''INSERT INTO active_setups 
               (user_id, symbol, timeframe, setup_id, side, status, 
                idea_score, trade_score, levels_json, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, symbol, timeframe, setup_id, side, status,
             idea_score, trade_score, levels_json, now, expires_at)
        )
        self.conn.commit()
        return setup_id

    def get_active_setups(self, user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active setups for user, optionally filtered by status"""
        now = int(time.time())
        
        if status:
            cur = self.conn.execute(
                '''SELECT * FROM active_setups 
                   WHERE user_id = ? AND status = ? AND expires_at > ? AND invalidated_at IS NULL
                   ORDER BY created_at DESC''',
                (user_id, status, now)
            )
        else:
            cur = self.conn.execute(
                '''SELECT * FROM active_setups 
                   WHERE user_id = ? AND expires_at > ? AND invalidated_at IS NULL
                   ORDER BY created_at DESC''',
                (user_id, now)
            )
        
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        
        setups = []
        for row in rows:
            setup = dict(zip(columns, row))
            if setup['levels_json']:
                setup['levels'] = json.loads(setup['levels_json'])
            setups.append(setup)
        
        return setups

    def upgrade_setup_to_trade(self, setup_id: str, trade_score: Optional[int] = None) -> bool:
        """Upgrade IDEA setup to TRADE status"""
        now = int(time.time())
        cur = self.conn.execute(
            '''UPDATE active_setups 
               SET status = 'TRADE', trade_score = ?, confirmed_at = ?
               WHERE setup_id = ? AND status = 'IDEA' AND invalidated_at IS NULL''',
            (trade_score, now, setup_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def invalidate_setup(self, setup_id: str) -> bool:
        """Mark setup as invalid/expired"""
        now = int(time.time())
        cur = self.conn.execute(
            'UPDATE active_setups SET invalidated_at = ? WHERE setup_id = ?',
            (now, setup_id)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def cleanup_expired_setups(self) -> int:
        """Remove expired setups"""
        now = int(time.time())
        cur = self.conn.execute(
            'DELETE FROM active_setups WHERE expires_at < ? OR invalidated_at IS NOT NULL',
            (now,)
        )
        self.conn.commit()
        return cur.rowcount
    
    def cleanup_expired_setups_for_user(self, user_id: str) -> int:
        """Remove expired setups for a specific user"""
        now = int(time.time())
        cur = self.conn.execute(
            '''DELETE FROM active_setups 
               WHERE user_id = ? AND (expires_at < ? OR invalidated_at IS NOT NULL)''',
            (user_id, now)
        )
        self.conn.commit()
        return cur.rowcount

    def get_existing_idea(self, user_id: str, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Check if there's already an active IDEA for this symbol/timeframe"""
        now = int(time.time())
        cur = self.conn.execute(
            '''SELECT * FROM active_setups 
               WHERE user_id = ? AND symbol = ? AND timeframe = ? 
               AND status = 'IDEA' AND expires_at > ? AND invalidated_at IS NULL
               LIMIT 1''',
            (user_id, symbol, timeframe, now)
        )
        row = cur.fetchone()
        if not row:
            return None
            
        columns = [desc[0] for desc in cur.description]
        setup = dict(zip(columns, row))
        if setup['levels_json']:
            setup['levels'] = json.loads(setup['levels_json'])
        return setup

    # ---------- dedup ----------
    def has_dedup_key(self, dedup_key: str) -> bool:
        cur = self.conn.execute('SELECT 1 FROM signals_sent WHERE dedup_key=? LIMIT 1', (dedup_key,))
        return cur.fetchone() is not None

    def save_sent_signal(
        self,
        tg_user_id: str,
        dedup_key: str,
        symbol: str,
        timeframe: str,
        signal_type: str,
        candle_ts: int,
        score_total: Optional[int],
        payload: dict,
    ) -> None:
        now = int(time.time())
        self.conn.execute(
            'INSERT INTO signals_sent(tg_user_id,dedup_key,symbol,timeframe,signal_type,candle_ts,score_total,payload_json,sent_at) '
            'VALUES(?,?,?,?,?,?,?,?,?)',
            (
                tg_user_id,
                dedup_key,
                symbol,
                timeframe,
                signal_type,
                candle_ts,
                score_total,
                json.dumps(payload, ensure_ascii=False, default=str),
                now,
            ),
        )
        self.conn.commit()

    # ---------- cooldown ----------
    def is_in_cooldown(self, tg_user_id: str, key: str) -> bool:
        now = int(time.time())
        cur = self.conn.execute('SELECT expires_at FROM cooldowns WHERE tg_user_id=? AND key=?', (tg_user_id, key))
        row = cur.fetchone()
        return row is not None and int(row['expires_at']) > now

    def set_cooldown(self, tg_user_id: str, key: str, seconds: int) -> None:
        expires_at = int(time.time()) + seconds
        self.conn.execute(
            'INSERT INTO cooldowns(tg_user_id,key,expires_at) VALUES(?,?,?) '
            'ON CONFLICT(tg_user_id,key) DO UPDATE SET expires_at=excluded.expires_at',
            (tg_user_id, key, expires_at),
        )
        self.conn.commit()

    # ---------- scan cursor ----------
    def get_cursor(self, user_id: str) -> int:
        """Get current scan cursor position for user"""
        cur = self.conn.execute(
            'SELECT idx FROM scan_cursor WHERE user_id = ?', 
            (user_id,)
        )
        row = cur.fetchone()
        return int(row['idx']) if row else 0

    def set_cursor(self, user_id: str, idx: int) -> None:
        """Set scan cursor position for user"""
        now = int(time.time())
        self.conn.execute(
            '''INSERT INTO scan_cursor(user_id, idx, updated_at) 
               VALUES(?, ?, ?) 
               ON CONFLICT(user_id) DO UPDATE SET 
               idx=excluded.idx, updated_at=excluded.updated_at''',
            (user_id, idx, now)
        )
        self.conn.commit()

    # ---------- symbol rotation ----------
    def get_last_sent(self, user_id: str, topic: str, symbol: str) -> Optional[int]:
        """Get last sent timestamp for symbol in topic"""
        cur = self.conn.execute(
            '''SELECT last_sent_at FROM symbol_rotation 
               WHERE user_id = ? AND topic = ? AND symbol = ?''',
            (user_id, topic, symbol)
        )
        row = cur.fetchone()
        return int(row['last_sent_at']) if row else None

    def set_last_sent(self, user_id: str, topic: str, symbol: str, timestamp: Optional[int] = None) -> None:
        """Set last sent timestamp for symbol in topic"""
        if timestamp is None:
            timestamp = int(time.time())
        self.conn.execute(
            '''INSERT INTO symbol_rotation(user_id, topic, symbol, last_sent_at) 
               VALUES(?, ?, ?, ?) 
               ON CONFLICT(user_id, topic, symbol) DO UPDATE SET 
               last_sent_at=excluded.last_sent_at''',
            (user_id, topic, symbol, timestamp)
        )
        self.conn.commit()

    def can_send_symbol(self, user_id: str, topic: str, symbol: str, rotation_hours: int) -> bool:
        """Check if symbol can be sent based on rotation policy"""
        last_sent = self.get_last_sent(user_id, topic, symbol)
        if last_sent is None:
            return True
        
        now = int(time.time())
        min_interval = rotation_hours * 3600  # Convert hours to seconds
        return (now - last_sent) >= min_interval
