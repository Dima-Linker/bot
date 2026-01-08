# 🧰 Candle-Cache + „Scannt nur ~45 Paare“ Diagnose & Fix (Master-Guide)

Du hast 2 Themen:
1) **API-Optimierung (Candle Cache / Incremental Updates)**  
2) **Verdacht: Scanner läuft nicht über alle Coins (du siehst seit Tagen dieselben ~45 Paare)**

Dieses Dokument ist so geschrieben, dass du es **1:1 umsetzen** kannst.

---

## 1) Warum du „immer dieselben Paare“ siehst (typische Ursachen)

Wenn du dauerhaft nur ~45 Märkte „in den Logs/Alerts“ siehst, liegt es fast immer an einem dieser Punkte:

### A) Du scannst wirklich nur eine Teilmenge (Bug/Filter)
- irgendwo wird `symbols = symbols[:45]` oder eine Watchlist genutzt
- ein Filter wie `if symbol not in ALLOWED:` greift
- es wird nur „Top Volume“ oder „Popular“ returned (falscher Endpoint / falsche Filterung)

### B) Der Scan bricht nach ~45 ab (Exception/Timeout) – und startet dann neu
- im Loop passiert ein Fehler und du machst `return` statt `continue`
- ein Timeout wirft Exception, der outer loop beendet den gesamten Scan
- du nutzt `asyncio.gather()` ohne `return_exceptions=True` → **eine** Exception killt die ganze Batch
- Rate-Limit/HTTP-Fehler nach X Calls → danach kommt nichts mehr

### C) Du scannst zwar alle, aber sendest nur für dieselben
- Dedup/Cooldown blockt fast alles außer ein paar „Trigger-Heavy“ Coins
- du routest/printest nur für Coins, die Features liefern (Filter)
- du loggst nur die ersten N Coins zur Debug-Zeit

### D) Scheduler / Concurrency limitiert
- du hast ein `Semaphore(45)` oder Pool-Limit und wartest nie auf restliche Tasks
- du startest den nächsten Scan bevor der alte fertig ist → der alte wird abgebrochen

---

## 2) Sofort-Test: Beweise, ob wirklich alle Symbole gescannt werden

### 2.1 Scan-Metriken pro Scan-Lauf (Pflicht)
Am Anfang eines Scans:
- `expected_symbols = len(symbols)` (z.B. 531)
- `scanned_symbols = 0`
- `errors = 0`
- `kline_calls = 0`

Am Ende:
- logge **immer**:
```
[SCAN-END] expected=531 scanned=531 ok=520 errors=11 duration=xxx
```

### 2.2 Fortschritt-Log jede 25 Symbole (damit du es live siehst)
```
[SCAN-PROGRESS] i=25/531 last=...
[SCAN-PROGRESS] i=50/531 last=...
...
```

### 2.3 „Welche Symbole wurden gescannt?“ – Debug-File (optional, sehr hilfreich)
Pro Scan schreibe eine Datei:
- `data/scan_last_symbols.txt`
- mit den letzten 531 Symbolnamen (oder z.B. die ersten 100 + letzten 100)

So siehst du sofort: läuft er komplett oder stoppt er.

---

## 3) Fix-Patterns (Code-Hinweise, die fast immer die Ursache sind)

### 3.1 Niemals `return` im Symbol-Loop
Schlecht:
```python
for s in symbols:
    candles = fetch(...)
    if not candles:
        return  # ❌ killt den ganzen scan
```

Richtig:
```python
for s in symbols:
    try:
        candles = fetch(...)
        if not candles:
            continue
    except Exception:
        continue
```

### 3.2 `asyncio.gather` nur mit `return_exceptions=True`
Schlecht:
```python
await asyncio.gather(*tasks)  # ❌ 1 error kills all
```

Richtig:
```python
results = await asyncio.gather(*tasks, return_exceptions=True)
for r in results:
    if isinstance(r, Exception):
        errors += 1
```

### 3.3 Rate-Limits: Retry + Backoff statt Abbruch
Wenn HTTP 429/418/5xx:
- `sleep(0.5–2s)` + retry 1–3x
- danach `continue`, nicht `return`

---

## 4) API-Optimierung: Candle Cache / Incremental Updates (damit alles stabil läuft)

Du holst aktuell oft **220 Kerzen pro Symbol/TF**. Das ist für jeden 5-Minuten Scan unnötig.

### Ziel
- **Initial**: 220 Kerzen laden
- danach: nur **neue Kerzen seit dem letzten Timestamp**
- Cache pro `(symbol, timeframe)` im RAM (und optional persistiert)

---

## 5) Candle Cache – Datenstruktur

Im Scanner z.B. global:
```python
CANDLE_CACHE = {
  ("BTCUSDT", "15m"): {
      "last_ts": 1767509100000,
      "candles": [...]
  }
}
```

**Regeln:**
- max `MAX_CANDLES = 220`
- bei Update: append neue candles, trimme alte

---

## 6) Incremental Fetch – Logik

### 6.1 Beim ersten Mal (Cache leer)
- `fetch_klines(symbol, tf, limit=220)`  
- setze `last_ts` auf letzte Kerze

### 6.2 Danach
- `fetch_klines(symbol, tf, after=last_ts)` oder `startTime=last_ts+1`  
- Wenn API kein „after“ hat:
  - hole `limit=10` und merge nur die neueren (timestamp check)

### 6.3 Merge-Algorithmus
- verwende timestamp als Key
- überschreibe die letzte Kerze, falls sie „incomplete“ ist (noch nicht geschlossen)
- optional: „nur closed candle“ nutzen (candle close trigger)

---

## 7) Candle-Close Trigger (sehr empfohlen)
Viele Indikatoren sind sauberer auf **Close**.

Regel:
- 15m: nur auswerten, wenn neue 15m Kerze geschlossen hat
- 1h: nur bei neuer 1h Kerze
- 4h: nur bei neuer 4h Kerze

Das reduziert API-Calls massiv und macht Signale stabiler.

---

## 8) Warum du wenig „neue Signale“ bekommst (ohne Bug)
Auch wenn der Scan korrekt läuft, kann es sein, dass du immer gleiche Coins siehst, weil:
- dein PUMP/Volume/Fib Filter triggert nur bei „bewegten“ Coins
- Dedup/Cooldown blockt sehr viel
- du schaust nur in 1 Topic, während andere Topics aktiv sind

### Debug-Check (Pflicht)
Logge pro Scan:
- `features_found_total`
- `alerts_sent_total`
- `top10_symbols_by_features`

So erkennst du: Scan läuft, aber Filter/Cooldown dominieren.

---

## 9) Konkrete Debug-Commands (Telegram)
Empfohlen (falls nicht vorhanden):

### `/scan_status`
Antwort:
- last scan time
- duration
- expected/scanned
- errors
- last 5 symbols scanned

### `/scan_sample 20`
Antwort:
- 20 zufällige Symbole aus der Symbol-Liste (beweist Vielfalt)

### `/debug_symbols`
Antwort:
- `len(symbols)` + `first 10` + `last 10`

---

## 10) Quick-Fix Checkliste (in Reihenfolge)

1) **Symbol-Liste debuggen**
   - Log: `len(symbols)` muss 531 sein
   - log first/last 10 symbols

2) **Scan-End Summary einbauen**
   - expected/scanned/errors/duration

3) **Kein return im loop**
   - alle Fehler → `continue`

4) **Async gather fix**
   - `return_exceptions=True`

5) **Cache + incremental candles**
   - initial 220, danach 1–10 neue

6) **Candle-close Trigger**
   - nur rechnen wenn neue candle closed

---

## 11) Erfolgskriterium (so weißt du, dass es wirklich läuft)
Du siehst in Logs:
- `[SCAN-END] expected=531 scanned=531 ...` **bei jedem Scan**
- `errors` < 5% dauerhaft
- unterschiedliche Symbole im „last scanned“ Bereich
- Pump/SMC/Fib Alerts variieren je nach Markt

---

Wenn du willst, kann ich dir als nächsten Schritt eine **zweite MD** schreiben, die **genau** zu deinem aktuellen Repo passt (Datei/Function-Namen), wenn du mir sagst:
- ob du `asyncio` nutzt oder Thread-Loop
- in welcher Datei die Symbol-Loop ist (`scanner/runner.py` wahrscheinlich)
