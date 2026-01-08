# ✅ FIX GUIDE: Scan-Lock + Chunking + Selector (collect→select→send) – FINAL

Ziel:  
- **Kein Overlap mehr** (neuer Scan startet nicht, solange der alte läuft)  
- **Scans werden planbar schnell** (Chunking / Round-Robin statt 531×3TF immer)  
- **Selector funktioniert wirklich** (collect → select → send am Ende)  
- **Mehr Vielfalt** (Altcoins kommen dran, nicht nur BTC/ETH/XRP)

---

## 0) Warum es „loopt“
Dein Scheduler tickt alle **5 Minuten**, aber ein Full-Scan dauert länger.  
⇒ Scan A läuft noch, Scan B startet → Logs wirken wie Restart/Loop.  
⇒ Der Selector wird evtl. nie sauber „am Ende“ ausgeführt.

**Fix = Scan-Lock + Chunking + End-of-scan Summary**

---

## 1) Scan-Lock („Skip if running“) – Pflicht

### 1.1 Minimal-Variante (single process)
In `scanner/scheduler.py` (oder da, wo `scheduler_loop` lebt):

```python
import time

SCAN_RUNNING = False

def scheduler_loop(scan_fn, interval_seconds: int):
    global SCAN_RUNNING
    while True:
        start = time.time()

        if SCAN_RUNNING:
            print("[SCHED] SKIP: previous scan still running")
        else:
            SCAN_RUNNING = True
            try:
                scan_fn()
            except Exception as e:
                print(f"[SCHED] scan_fn error: {e}")
            finally:
                SCAN_RUNNING = False

        duration = time.time() - start
        sleep_for = max(1, interval_seconds - int(duration))
        time.sleep(sleep_for)
```

✅ Ergebnis: **kein** überlappender Scan mehr.

### 1.2 Robust (für später Multi-Process)
Später kannst du DB-Lock (SQLite) oder File-Lock nutzen.  
Für jetzt reicht 1.1.

---

## 2) Chunking (Round-Robin) – damit es schnell bleibt

Du willst nicht jedes Mal 531 Symbole × 3 TF holen.  
Stattdessen scannst du pro Zyklus z.B. 80–150 Symbole.

### 2.1 Parameter
- `CHUNK_SIZE = 100` (Startwert)
- `SYMBOLS_TOTAL = len(symbols)`
- `cursor` merkt sich, wo du warst.

### 2.2 Cursor speichern (DB empfohlen)
Neue Tabelle z.B. `scan_cursor`:

```sql
CREATE TABLE IF NOT EXISTS scan_cursor (
  user_id INTEGER PRIMARY KEY,
  idx INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);
```

Repo-Funktionen:
- `get_cursor(user_id) -> int`
- `set_cursor(user_id, idx)`

### 2.3 Chunk Auswahl
In `scanner/runner.py`:

```python
def get_symbol_chunk(symbols, start_idx, chunk_size):
    n = len(symbols)
    end_idx = start_idx + chunk_size
    if end_idx <= n:
        chunk = symbols[start_idx:end_idx]
        next_idx = end_idx % n
    else:
        chunk = symbols[start_idx:] + symbols[:end_idx - n]
        next_idx = end_idx - n
    return chunk, next_idx
```

Dann pro User:

```python
cursor = repo.get_cursor(user_id)
chunk, next_cursor = get_symbol_chunk(symbols, cursor, CHUNK_SIZE)
repo.set_cursor(user_id, next_cursor)
```

✅ Ergebnis:
- Jeder Tick scannt andere Märkte
- Nach ~6 Ticks sind alle 531 durch
- Du bekommst **viel mehr Vielfalt** statt “immer die ersten Coins”

---

## 3) Timeframe-Optimierung (optional, aber stark empfohlen)

Wenn du alle 5 Minuten tickst:
- 15m hat selten neue Kerze (nur alle 15 Minuten)
- 1h alle 60 Minuten
- 4h alle 240 Minuten

**Candle-Close Trigger:**
- Analysiere einen TF nur, wenn eine neue Kerze geschlossen hat.
- Sonst skip (spart Zeit + Calls + mehr Stabilität).

Implementation-Idee:
- pro `(symbol, tf)` `last_closed_ts` merken
- wenn gleich → skip.

---

## 4) Selector richtig einhängen (collect→select→send)

Das ist der wichtigste Teil, damit Diversity wirklich wirkt.

### 4.1 Pro Symbol NICHT sofort senden
Falsch:
- im Symbol-Loop direkt senden.

Richtig:
- pro Symbol Features → Candidate(s) erstellen → in Liste sammeln.

```python
all_candidates = []
for symbol in chunk:
    candidates = analyze_symbol(...)
    all_candidates.extend(candidates)

selected, summary = selector.select(all_candidates)
send(selected)
send(summary)
```

### 4.2 Hard Rules
- **max 1 Alert pro Symbol pro Scan** (egal welches Topic)
- **Topic Caps** (z.B. COMBO 5, IDEA 6, FIB 10, LIQ 10, PUMP 6)
- Global cap z.B. 20

### 4.3 Routing NICHT aus Text ableiten
Candidate muss **topic** haben:
- `candidate.topic = "COMBO" | "IDEA" | "FIBONACCI" | "LIQUIDITY" | "PUMP" | "TEST"`

Router nutzt nur dieses Feld.

---

## 5) Two-Tier System (Elite + Radar Summary)

Damit du viele Coins siehst ohne Spam:

### Tier A (Elite)
- Top N pro Topic → **Einzelpost** (mit Chart wenn du willst)

### Tier B (Radar Summary)
- Rest als 1 Nachricht:
```
📡 Market Radar (15m)
• ADAUSDT +6.1% (PUMP) score 78
• OPUSDT fib zone hit (FIB) score 65
...
```

Empfehlung:
- Summary pro Topic ODER 1 globale Summary.

---

## 6) End-of-Scan Logging (damit du IMMER weißt was los ist)

Am Ende jedes Scan-Ticks:

```
[SCAN-END] total_symbols=531 chunk=100 start_idx=200 next_idx=300
[SCAN-END] candidates=184 unique_symbols=133
[SCAN-END] selected=20 unique_symbols_selected=20
[SCAN-END] topic_counts COMBO=5 IDEA=6 FIB=5 LIQ=4 PUMP=0
[SCAN-END] errors=12 duration=148s
```

Das ist dein „Truth Meter“.

---

## 7) Empfohlene Startwerte

- Scheduler interval: **300s (5min)** okay, aber nur mit Scan-Lock
- Chunk: **100**
- Caps:
  - COMBO 5
  - IDEA 6
  - FIB 10
  - LIQ 10
  - PUMP 6
  - TOTAL 20
- DEBUG_COOLDOWN=1 nur für Tests

---

## 8) Minimaler Rollout Plan (sicher)

### Schritt 1
✅ Scan-Lock einbauen  
→ beobachte: „SKIP previous scan still running“ / keine Overlaps

### Schritt 2
✅ Chunking aktivieren (100)  
→ du siehst andere Symbole in Logs (first/last)

### Schritt 3
✅ Selector an Ende (collect→select→send)  
→ topic_counts + unique_symbols_selected prüfen

### Schritt 4
✅ Summary Tier hinzufügen (Radar)  
→ mehr Überblick, weniger Spam

---

## 9) Wie du erkennst, dass es „fertig“ ist
- Kein Scan-Overlap mehr
- Jeder Tick scannt andere Symbole (cursor bewegt sich)
- Telegram zeigt nicht nur BTC/ETH/XRP, sondern auch Alts
- COMBO landet nie in IDEA
- Du bekommst wenige Elite Posts + Radar Summary

---

Wenn du willst, kann ich dir als Nächstes eine zweite MD schreiben:
**„Candle Cache + Incremental Klines“**, damit der Chunk-Scan noch schneller wird.
