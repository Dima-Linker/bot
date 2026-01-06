import hashlib
import json


def make_dedup_key(tg_user_id: str, symbol: str, timeframe: str, signal_type: str, candle_ts: int, levels: dict, version: str = 'v1') -> str:
    zone_hint = json.dumps(levels or {}, sort_keys=True)
    raw = f"{tg_user_id}|{symbol}|{timeframe}|{signal_type}|{candle_ts}|{zone_hint}|{version}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()