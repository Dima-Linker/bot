# ✅ FIX + ERWEITERUNG: Event-Loop Lock Bug + Diversity/Rotation + Radar Summary

Dieses Dokument behebt **sofort** deinen Fehler:
> `<asyncio.locks.Lock ...> is bound to a different event loop`

und erweitert das System so, dass du **nicht immer dieselben Coins** bekommst:
- Rotation / Per-Symbol Cooldown
- Market Radar Summary (statt Spam)
- stabileres Sending (Queue/Worker)

---

## 1) Problem 1: „Lock bound to a different event loop“ (kritisch)

### 1.1 Warum das passiert
Du nutzt sehr wahrscheinlich:
- Telegram Bot läuft in **Event Loop A**
- Scanner/Worker läuft in **Thread / Event Loop B**
- Ein globaler `asyncio.Lock()` wurde in Loop A erstellt, aber in Loop B verwendet (oder umgekehrt)

`asyncio.Lock` darf **nicht loop-übergreifend** benutzt werden.

### 1.2 Schneller Fix (empfohlen): `threading.Lock` statt `asyncio.Lock`
Wenn du **Threads** nutzt (Scanner Thread + Telegram Polling):
- benutze `threading.Lock` für Synchronisation zwischen Threads

✅ Suche im Projekt nach:
```python
asyncio.Lock(
```

❌ Beispiel (Problem):
```python
import asyncio
SEND_LOCK = asyncio.Lock()
```

✅ Fix:
```python
import threading
SEND_LOCK = threading.Lock()
```

Und beim Senden:
```python
def safe_send(send_fn, *args, **kwargs):
    with SEND_LOCK:
        return send_fn(*args, **kwargs)
```

> Wenn dein send_fn async ist: siehe 1.3.

### 1.3 Wenn Senden async ist: `run_coroutine_threadsafe`
Falls dein Scanner in einem Thread läuft und Telegram `application` einen Async-Loop hat:

```python
import asyncio

def send_from_thread(app, coro):
    future = asyncio.run_coroutine_threadsafe(coro, app.bot.loop)
    return future.result(timeout=30)
```

Dann:
```python
with SEND_LOCK:
    send_from_thread(application, application.bot.send_message(...))
```

### 1.4 Alternative (nur wenn du 100% in EINEM Loop bist): Lock im Loop erstellen
Wenn Scanner als async Task im selben Loop läuft:
```python
async def router_send(app, ...):
    lock = app.bot_data.setdefault("send_lock", asyncio.Lock())
    async with lock:
        ...
```

---

## 2) Problem 2: Du siehst trotzdem oft „ähnliche Coins“ (Diversity-Policy)

Du hast Chunking + Selector, aber ohne „Rotation“ können trotzdem bestimmte Coins häufig gewinnen.

### 2.1 Rotation Rule: „Symbol-Rotation“ pro Topic
Regel:
- Ein Symbol darf pro Topic nur **alle X Stunden** als Elite gesendet werden.

Empfohlene Default-Werte:
- COMBO: 6h
- IDEA: 3h
- FIB: 2h
- LIQ: 2h
- PUMP: 1h

### 2.2 Umsetzung in DB
Neue Tabelle `symbol_rotation`:

```sql
CREATE TABLE IF NOT EXISTS symbol_rotation (
  user_id INTEGER NOT NULL,
  topic TEXT NOT NULL,
  symbol TEXT NOT NULL,
  last_sent_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, topic, symbol)
);
```

Repo:
- `get_last_sent(user_id, topic, symbol) -> ts|None`
- `set_last_sent(user_id, topic, symbol, ts)`

Check im Selector (vor Auswahl):
```python
if now - last_sent_at < rotation_seconds[topic]:
    skip
```

> Vorteil: Du bekommst automatisch mehr Altcoins in Elite.

---

## 3) Erweiterung: Market Radar Summary (2-Tier System)

Ziel:
- **Elite**: wenige Top-Posts (mit Chart)
- **Radar**: eine kompakte Liste der „Good Setups“ (ohne Chart)

### 3.1 Regeln
- Elite Caps (z.B. total=5–12)
- Radar Caps (z.B. 15–40) als 1 Nachricht pro Scan

Beispiel Radar Message:
```
📡 Market Radar (Chunk 100–199 | 15m/1h)

🧠 COMBO Kandidaten:
• RDNTUSDT 1h (score 392) – Fib + SMC
• ARPAUSDT 15m (score 381) – Pump + FVG

📐 FIB:
• OPUSDT 15m (score 72) – Golden Zone hit
• AAVEUSDT 1h (score 68) – Retrace zone

💧 LIQ:
• MANAUSDT 15m – Sweep + Reclaim

Hinweis: Radar = Heads-up, kein Entry.
```

### 3.2 Umsetzung
Dein Selector gibt zurück:
- `selected_elite[]`
- `selected_radar[]`

Senden:
- Elite: einzeln (Charts optional)
- Radar: 1 Sammelpost in Topic „IDEA“ oder eigenes Topic „📡 RADAR“

---

## 4) Fix: „COMBO landet in IDEA“ (Routing-Bug)

### 4.1 Regel
Routing darf **niemals** aus Text/Score erraten werden.

Jeder Candidate muss ein Feld haben:
- `topic` (Enum/String)

Beispiel:
```python
candidate.topic = "COMBO"
```

Telegram Router:
```python
thread_id = TOPIC_THREAD_IDS[candidate.topic]
```

### 4.2 Hard Assertions (Debug)
Vor send:
```python
assert candidate.topic in TOPIC_THREAD_IDS
```

---

## 5) Stabiler Versand: Queue + Worker (optional, empfohlen)
Wenn du Charts und mehrere Messages hast: nutze eine Queue.

### 5.1 Pattern
- Scanner produziert send_jobs
- Sender-Worker konsumiert nacheinander (rate limit safe)
- Lock wird dann oft überflüssig

Pseudo:
```python
from queue import Queue
SEND_Q = Queue()

def sender_worker():
    while True:
        job = SEND_Q.get()
        try:
            job()
        finally:
            SEND_Q.task_done()
```

---

## 6) Monitoring, das immer stimmt (Bug in deinem Report)
Du hattest im Log:
- `candidates=201 unique_symbols=96`
aber später:
- `Unique symbols with alerts: 0`

Das ist nur ein Zählfehler im Debug-Report.
Fix: nutze **dieselbe** Variable wie oben.

Empfohlenes End-of-Scan Log:
```
SCAN DONE: candidates=201 unique_symbols=96
SELECTED: total=5 unique_symbols_selected=5
TOPICS: combo=5 fib=0 liq=0 pump=0 idea=0
ROTATION_SKIPS: 12
SEND_ERRORS: 0
```

---

## 7) Rollout Reihenfolge (wichtig)

1) **Lock Bug fixen** (threading.Lock oder single-loop)
2) 1–2 Scans laufen lassen → keine Routing-Send Fehler mehr
3) Rotation/Per-Symbol Cooldown aktivieren
4) Radar Summary hinzufügen
5) Optional: Queue/Worker

---

## 8) Quick Defaults (Startwerte)

- Elite Total: 8
- Elite Caps:
  - COMBO 5
  - IDEA 3
  - FIB 6
  - LIQ 6
  - PUMP 4
- Rotation:
  - COMBO 6h
  - IDEA 3h
  - FIB 2h
  - LIQ 2h
  - PUMP 1h
- Scheduler interval: 5min + Scan-Lock + Chunking

---

Wenn du willst, mache ich dir als nächsten Schritt eine zweite Datei:
**„Wie du Scanner + Telegram komplett in EINEM asyncio loop laufen lässt (PTB JobQueue)“**
→ dann gibt es diese Lock-Probleme nie wieder.
