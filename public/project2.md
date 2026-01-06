# Telegram Crypto-Signal Hub-Bot (Python) — Detaillierte Umsetzung & Erweiterungen
> Ziel: 1 Telegram-Bot / 1 Chat, aber getrennte Bereiche (Module) im UX.
> Module können einzeln aktiviert werden (Feed oder nur Combo-Input). Zusätzlich gibt es eine Combo/Premium-Engine,
> die mehrere Bedingungen kombiniert und nur hochwertige Signale sendet.
> State (Dedup/Cooldown/Settings) wird mit einer kleinen SQLite DB gespeichert (später leicht auf Postgres migrierbar).

## 0) Ausgangslage (dein aktueller Projektstand)
Du hast bereits ein Python-Telegrambot-Projekt ähnlich:

```text
TELEGRAMBOT/
  public/
  venv/
  .env
  config.py
  main.py
  run_bot.py
  smc_custom.py
  requirements.txt
  ...
```

Wir erweitern das Projekt ohne alles umzubauen: wir ergänzen klar getrennte Layer (DB, Scanner, Engine, Module, Bot-UX).

## 1) Ziel-Architektur (High Level)
**Data Flow pro Scan (alle 5 Minuten):**

```text
Bitget API → Candles (15m/1h/4h) → Module-Features → Decision Layer (Combo/Elite)
          → Dedup/Cooldown/Settings (SQLite) → Telegram Notifier (Message + optional Chart)
```

Warum DB? Ohne DB keine verlässliche Deduplizierung, Cooldowns, User-Settings, Verlauf/Stats.

## 2) Neue Ordner- & Dateistruktur (empfohlen)
Erweitere dein Projekt um:

```text
TELEGRAMBOT/
  db/
    schema.sql
    database.py
    repo.py

  engine/
    types.py
    presets.py
    decision.py
    dedup.py
    message_builder.py

  modules/
    volume.py
    fibo.py
    rsi_div.py
    macd.py
    smc.py

  scanner/
    bitget_client.py
    runner.py
    scheduler.py

  bot/
    handlers.py
    menus.py

  main.py (oder run_bot.py)
```

Hinweis: `smc_custom.py` kannst du erstmal weiter nutzen und in `modules/smc.py` importieren.

## 3) DB (SQLite) — Minimal & ausreichend fürs MVP
### 3.1 `db/schema.sql`

```sql
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
```

### 3.2 `db/database.py`

```python
import sqlite3
from pathlib import Path


def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str, schema_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = get_conn(db_path)
    with open(schema_path, 'r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.commit()
    return conn
```

### 3.3 `db/repo.py` (Settings + Dedup + Cooldown)

```python
import json
import time


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
        score_total: int | None,
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
                json.dumps(payload, ensure_ascii=False),
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
```

## 4) Engine: Types, Presets, Decision, Dedup, Message
### 4.1 `engine/types.py`

```python
from dataclasses import dataclass
from typing import Literal, Optional

Direction = Literal['long', 'short', 'both']
Strength = Literal['weak', 'medium', 'strong', 'elite']


@dataclass
class FeatureResult:
    module: str
    symbol: str
    timeframe: str
    candle_ts: int
    direction: Direction
    strength: Strength
    score: int
    reasons: list[str]
    levels: Optional[dict] = None
    tags: Optional[list[str]] = None
```

### 4.2 `engine/presets.py`

```python
PRESETS = {
    'conservative': {
        'combo_min_score': 80,
        'cooldown_hours': 6,
        'volume_elite_mult': 8.0,
    },
    'normal': {
        'combo_min_score': 70,
        'cooldown_hours': 4,
        'volume_elite_mult': 7.0,
    },
    'aggressive': {
        'combo_min_score': 60,
        'cooldown_hours': 2,
        'volume_elite_mult': 6.0,
    },
}
```

### 4.3 `engine/decision.py` (Elite ODER Combo)

```python
from .types import FeatureResult

LEVEL_MODULES = {'fibo', 'smc'}
MOMENTUM_MODULES = {'rsi_div', 'macd'}
PARTICIPATION_MODULES = {'volume'}


def _categories_present(features: list[FeatureResult]) -> set[str]:
    cats = set()
    for f in features:
        if f.module in LEVEL_MODULES:
            cats.add('level')
        if f.module in MOMENTUM_MODULES:
            cats.add('momentum')
        if f.module in PARTICIPATION_MODULES:
            cats.add('participation')
    return cats


def _merge_levels(features: list[FeatureResult]) -> dict:
    merged = {}
    for f in features:
        if f.levels:
            merged[f.module] = f.levels
    return merged


def decide_signal(features: list[FeatureResult], min_score: int) -> dict | None:
    if not features:
        return None

    # A) Single-Trigger (Elite)
    elite = [f for f in features if f.strength == 'elite']
    if elite:
        top = sorted(elite, key=lambda x: x.score, reverse=True)[0]
        return {
            'type': f"module:{top.module}",
            'score_total': top.score,
            'features': [top],
            'levels': top.levels or {},
            'reasons': top.reasons,
        }

    # B) Confluence
    total = sum(f.score for f in features)
    cats = _categories_present(features)

    if total >= min_score and len(cats) >= 2:
        return {
            'type': 'combo',
            'score_total': total,
            'features': features,
            'levels': _merge_levels(features),
            'reasons': [r for f in features for r in f.reasons],
        }

    return None
```

### 4.4 `engine/dedup.py`

```python
import hashlib
import json


def make_dedup_key(tg_user_id: str, symbol: str, timeframe: str, signal_type: str, candle_ts: int, levels: dict, version: str = 'v1') -> str:
    zone_hint = json.dumps(levels or {}, sort_keys=True)
    raw = f"{tg_user_id}|{symbol}|{timeframe}|{signal_type}|{candle_ts}|{zone_hint}|{version}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()
```

### 4.5 `engine/message_builder.py`

```python
MODULE_TAGS = {
    'volume': '[VOLUME] 🔥',
    'fibo': '[FIBO] 🧲',
    'rsi_div': '[DIVERGENZ] 🟢',
    'macd': '[MACD] 🔵',
    'smc': '[SMC] 🏦',
}


def build_message(symbol: str, timeframe: str, decision: dict) -> str:
    signal_type = decision['type']
    score_total = decision.get('score_total')

    if signal_type == 'combo':
        header = '[COMBO] 🧠 High-Quality Setup'
    else:
        mod = signal_type.split(':', 1)[1]
        header = f"{MODULE_TAGS.get(mod, '[MODUL]')} Starkes Signal"

    reasons = decision.get('reasons', [])
    reasons_text = '\n'.join([f"• {r}" for r in reasons][:8])

    score_text = f"\n\n📊 Score: {score_total}" if score_total is not None else ''

    return (
        f"{header}\n"
        f"🪙 {symbol} (USDT Perp)\n"
        f"🕒 TF: {timeframe}\n\n"
        f"{reasons_text}"
        f"{score_text}\n"
        f"\n⚠️ Hinweis: Keine Finanzberatung. Risiko-Management beachten."
    )
```

## 5) Module: Konkrete Implementierung (MVP)
Wichtig: Module arbeiten auf der **letzten geschlossenen Kerze** (`candles[-2]`).

### 5.1 `modules/volume.py` (schnellster Elite-Trigger)

```python
from engine.types import FeatureResult


def compute(symbol: str, timeframe: str, candles: list[dict], elite_mult: float = 7.0) -> FeatureResult | None:
    if len(candles) < 80:
        return None

    closed = candles[-2]
    vols = [c['volume'] for c in candles[-52:-2]]
    avg = sum(vols) / len(vols) if vols else 0
    mult = (closed['volume'] / avg) if avg > 0 else 0

    if mult < 4.0:
        return None

    direction = 'long' if closed['close'] > closed['open'] else 'short'

    if mult >= elite_mult:
        return FeatureResult(
            module='volume',
            symbol=symbol,
            timeframe=timeframe,
            candle_ts=closed['ts'],
            direction=direction,
            strength='elite',
            score=55,
            reasons=[f"MEGA Volume-Pump: {mult:.1f}× Ø (52 Kerzen)"],
            levels={'mult': mult, 'avg': avg},
            tags=['volume_pump'],
        )

    strength = 'strong' if mult >= 6 else 'medium'
    score = 40 if strength == 'strong' else 25

    return FeatureResult(
        module='volume',
        symbol=symbol,
        timeframe=timeframe,
        candle_ts=closed['ts'],
        direction=direction,
        strength=strength,
        score=score,
        reasons=[f"Volume erhöht: {mult:.1f}× Ø (52 Kerzen)"],
        levels={'mult': mult, 'avg': avg},
        tags=['volume_pump'],
    )
```

## 6) Scanner: Runner + Scheduler
### 6.1 `scanner/bitget_client.py` (Skeleton)

```python
class BitgetClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')

    def list_usdt_perp_symbols(self) -> list[str]:
        raise NotImplementedError

    def get_klines(self, symbol: str, timeframe: str, limit: int = 200) -> list[dict]:
        raise NotImplementedError
```

### 6.2 `scanner/runner.py` (Scan pro User)

```python
from engine.decision import decide_signal
from engine.dedup import make_dedup_key
from engine.message_builder import build_message
from engine.presets import PRESETS

TIMEFRAMES = ['15m', '1h', '4h']


def run_scan_for_user(repo, tg_user_id: str, bitget, telegram_send_fn, modules_registry: dict):
    settings = repo.get_settings(tg_user_id)
    preset = PRESETS.get(settings.get('preset', 'normal'), PRESETS['normal'])

    symbols = bitget.list_usdt_perp_symbols()
    watchlist = set(settings.get('watchlist', []))
    if watchlist:
        symbols = [s for s in symbols if s in watchlist]

    combo_min_score = int(settings.get('combo_min_score', preset['combo_min_score']))
    cooldown_seconds = int(preset['cooldown_hours']) * 3600

    for symbol in symbols:
        for tf in TIMEFRAMES:
            candles = bitget.get_klines(symbol, tf, limit=220)
            if len(candles) < 80:
                continue

            candle_ts = candles[-2]['ts']  # letzte geschlossene kerze

            features = []
            for module_name, module in modules_registry.items():
                mod_cfg = settings.get('modules', {}).get(module_name, {})
                if not mod_cfg.get('enabled', False):
                    continue

                if module_name == 'volume':
                    fr = module.compute(symbol, tf, candles, elite_mult=preset['volume_elite_mult'])
                else:
                    fr = module.compute(symbol, tf, candles)

                if fr and fr.candle_ts == candle_ts:
                    features.append(fr)

            decision = decide_signal(features, combo_min_score)
            if not decision:
                continue

            signal_type = decision['type']

            cooldown_key = f"{signal_type}:{symbol}:{tf}"
            if repo.is_in_cooldown(tg_user_id, cooldown_key):
                continue

            dedup_key = make_dedup_key(tg_user_id, symbol, tf, signal_type, candle_ts, decision.get('levels', {}))
            if repo.has_dedup_key(dedup_key):
                continue

            message = build_message(symbol, tf, decision)
            telegram_send_fn(tg_user_id, message)

            repo.save_sent_signal(
                tg_user_id=tg_user_id,
                dedup_key=dedup_key,
                symbol=symbol,
                timeframe=tf,
                signal_type=signal_type,
                candle_ts=candle_ts,
                score_total=decision.get('score_total'),
                payload={'decision': decision, 'features': [f.__dict__ for f in features]},
            )
            repo.set_cooldown(tg_user_id, cooldown_key, cooldown_seconds)
```

### 6.3 `scanner/scheduler.py` (alle 5 Minuten)

```python
import time


def scheduler_loop(scan_fn, interval_seconds: int = 300):
    while True:
        start = time.time()
        try:
            scan_fn()
        except Exception as e:
            print('Scan error:', e)
        duration = time.time() - start
        time.sleep(max(1, interval_seconds - int(duration)))
```

## 7) Telegram UX (1 Chat, getrennte Bereiche)
### 7.1 UX Prinzip
- `/start` zeigt Hauptmenü (Inline Buttons)
- `Module` zeigt Dashboard (pro Modul AN/AUS, Mode Feed/ComboOnly)
- Jede Signal-Nachricht trägt einen Tag: `[VOLUME]`, `[FIBO]`, `[COMBO]` usw.
- Watchlist & Presets im Menü

### 7.2 Settings-JSON Struktur (in `user_settings.modules_json`)

Beispiel:

```json
{
  "volume": {"enabled": true, "mode": "feed", "timeframes": ["15m","1h","4h"], "direction": "both"},
  "fibo": {"enabled": true, "mode": "comboOnly"}
}
```

## 8) Erweiterungen (konkret)
### 8.1 Deduplizierung & Cooldown — warum das Pflicht ist
- Dedup verhindert doppelte Signale bei gleichen Bedingungen
- Cooldown verhindert „Zone-Spam“ bei seitwärts laufenden Märkten

### 8.2 Candle-Close Trigger
- Arbeite immer mit `candles[-2]` (letzte geschlossene Kerze)
- Optional: kleine Delay-Window (2–5s), falls API leicht hinterherhinkt

### 8.3 Liquiditäts-/Spread-Filter (Stufe 3)
- K.O. wenn Spread zu hoch / Volumen zu niedrig
- Damit vermeidest du illiquide Perps, die nur Wicks produzieren

## 9) Startpunkt: Glue Code in `run_bot.py` (Pseudocode)

```python
from db.database import init_db
from db.repo import Repo
from scanner.scheduler import scheduler_loop
from scanner.runner import run_scan_for_user
from scanner.bitget_client import BitgetClient

from modules import volume


def telegram_send_fn(tg_user_id: str, message: str):
    # TODO: implementiere via python-telegram-bot oder aiogram
    pass


def main():
    conn = init_db('./data/bot.db', './db/schema.sql')
    repo = Repo(conn)

    bitget = BitgetClient(base_url='https://api.bitget.com')

    modules_registry = {
        'volume': volume,
        # später: 'fibo': fibo, 'rsi_div': rsi_div, 'macd': macd, 'smc': smc
    }

    def scan_all_users():
        # MVP: erstmal nur du (später: aus DB alle user laden)
        users = ['<DEIN_TG_USER_ID>']
        for u in users:
            run_scan_for_user(repo, u, bitget, telegram_send_fn, modules_registry)

    scheduler_loop(scan_all_users, interval_seconds=300)


if __name__ == '__main__':
    main()
```

## 10) Nächste sinnvolle Schritte (damit du sofort Fortschritt siehst)
1. DB einbauen (schema + init + repo)
2. Volume-Modul live bringen (Elite + dedup + cooldown)
3. Telegram-Menü: Module toggles + preset + watchlist
4. Danach: RSI Divergenz Modul
5. Danach: Fibo Golden Zone Modul
6. Danach: Combo Score feinjustieren + SMC hinzufügen

---

**Ende.**
