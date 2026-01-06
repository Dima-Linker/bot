# Fix-Plan: Konsistenz + „Pro“-Signalqualität (IDEA vs TRADE + Multi-TF Bias + Fib/FVG Cleanup)

Dieses Dokument beschreibt **konkret**, wie du die aktuellen Inkonsistenzen behebst, ohne deine bestehenden Module (SMC, Fib, RSI, MACD, Volume) wegzuwerfen.  
Ziel: **weniger “Bot würfelt”**, klarere Telegram-Ausgaben, sauberer „IDEA → TRADE“-Flow.

---

## TL;DR – Was du änderst (ohne alles umzubauen)

1) **Bias-Routing (4h → 1h → 15m)** einführen  
2) **Fib-Labels & Swing-Quelle** konsistent machen (Support/Resistance raus, stattdessen „Golden Zone Pullback/Retrace“)  
3) **FVG-Overlaps mergen** oder nur „side-consistent“ reporten  
4) **Pre-Send Validation (Gatekeeper)** vor dem Versand, der widersprüchliche Features **degradiert** oder **blockt**  
5) Telegram-Output strikt nach **IDEA vs TRADE** trennen

> Wichtig: Das ist **zusätzlich** zu deinen bestehenden Modulen – du ersetzt sie nicht.  
Du ergänzt eine Schicht „Routing + Validation + Messaging“.

---

## 1) Problem: Multi-TF Konflikte (15m/1h LONG, 4h SHORT)

### Ursache (typisch)
- Jedes TF wird “für sich” bewertet → Bot sendet mehrere „High-Quality Setups“, die sich widersprechen.
- Nutzer liest nur „LONG/SHORT“, nicht den Kontext.

### Lösung: Bias-Routing (HTF steuert LTF)
#### Definition
- **4h = Bias** (Trend/Regime)
- **1h = Filter** (Pullback/Übergang)
- **15m = Entry Timing** (Trigger & Confirmation)

#### Bias States (einfach, robust)
- `BULL`, `BEAR`, `NEUTRAL`

Beispiel-Rule (Start-Version):
- 4h `BULL`, wenn Struktur: HH/HL und Close über Value/Key-Level
- 4h `BEAR`, wenn LL/LH und Close unter Key-Level
- sonst `NEUTRAL`

#### Routing-Regeln
- Wenn 4h = `BEAR` und 15m zeigt `LONG` → **Countertrend**, nur `IDEA`, kein `TRADE` (oder blocken).
- Wenn 4h = `BULL` und 15m zeigt `SHORT` → analog.
- Erlaubnis-Matrix:

| 4h Bias | 15m Direction | Aktion |
|---|---|---|
| BULL | LONG | normal (IDEA/TRADE möglich) |
| BEAR | SHORT | normal (IDEA/TRADE möglich) |
| BULL | SHORT | **Countertrend**: nur IDEA oder block |
| BEAR | LONG | **Countertrend**: nur IDEA oder block |
| NEUTRAL | LONG/SHORT | normal, aber strengere Confirmation |

#### Telegram-Ausgabe (zwingend)
- Immer: **4h Bias** als Kontext in jeder Message.

---

## 2) Problem: Fib-Text widersprüchlich („Golden support“ UND „Golden resistance“)

### Ursache (typisch)
- Swing High/Low vertauscht → Fib invertiert.
- Mehrere Swing-Algorithmen pro TF → mehrere „Golden“-Treffer mit falscher Beschriftung.
- Labeling „support/resistance“ ist instabil, wenn der Bot die Richtung wechselt.

### Lösung: Fib standardisieren (single source of truth)
#### A) Einheitliche Swing-Definition pro TF
Du brauchst **pro Symbol + TF** genau einen aktiven Swing:
- `swing_low`, `swing_high` (+ timestamps/indices)
- `swing_direction`: `UP` oder `DOWN`

Minimal robust:
- Nimm die letzten bestätigten Swingpoints (z.B. ZigZag/Fractal oder Pivot-High/Low).
- Speichere diese in einem `SwingContext`.

#### B) Golden Zone Berechnung
- Golden Zone ist **immer**: `0.618–0.786`
- Für Long (Pullback in UP swing): Zone liegt **unter** dem Swing-High, über dem Swing-Low
- Für Short (Retrace in DOWN swing): Zone liegt **über** dem Swing-Low, unter dem Swing-High (invertiert berechnet)

**Wichtig**: Support/Resistance Labels rauswerfen.  
Stattdessen:  
- LONG: `Golden Zone Pullback (0.618–0.786)`
- SHORT: `Golden Zone Retrace (0.618–0.786)`

#### C) Immer mit Meta ausgeben (für Debug + Vertrauen)
- `swing_low`, `swing_high`
- `zone_low`, `zone_high`
- `hit_price`
- `swing_dir`

---

## 3) Problem: Bullish & Bearish FVG gleichzeitig / Overlaps

### Ursache (typisch)
- FVG-Detector markiert beide Seiten bei ähnlichen 3-Candle-Patterns.
- Zonen überlappen stark → Output wirkt wie „beides gleichzeitig“.
- Reporting ist “ungefiltert”.

### Lösung: Merge oder Side-Filter
#### Option A) Overlap Merge (empfohlen)
Wenn sich zwei Zonen stark überlappen:
- `overlap_ratio = overlap_range / min(rangeA, rangeB)`
- wenn `overlap_ratio >= 0.6` → merge zu einer Zone:
  - `low = min(lows)`, `high = max(highs)`
  - `bias = MIXED` (neutral)

Telegram:
- `FVG Zone (overlap/mixed): 82.14–82.27`

#### Option B) Side-Filter (strenger)
- LONG-Setups zeigen nur `Bullish FVG`
- SHORT-Setups zeigen nur `Bearish FVG`
- Overlaps werden ignoriert oder neutral gelabelt.

---

## 4) Neuer Baustein: Pre-Send Validation (Gatekeeper)

Schicht **nach** Module/Scoring, **vor** Telegram.

### Validations (MVP)
1) **Bias-Conflict**: 4h BEAR + 15m LONG → downgrade zu IDEA (Countertrend) oder block TRADE  
2) **Fib Sanity**: `zone_low < zone_high`, Zone innerhalb Swing-Range  
3) **FVG Overlap**: merge/neutral oder side-filter  
4) **Momentum Conflict**: LONG aber MACD/Struktur stark bearish → downgrade oder strengere Confirmation  
5) **Spam Control**: gleiche Level/Setup-ID → nicht neu senden, ggf. update

---

## 5) Messaging: IDEA vs TRADE strikt trennen

- `IDEA` = Watchlist / Heads-up  
- `TRADE` = Entry-Freigabe (Confirmation vorhanden)

**Nie** „High-Quality Setup“ schreiben, wenn im Text „Bestätigung abwarten“ steht.

### IDEA Template
- `🟡 [IDEA] Watchlist – Setup erkannt (kein Entry)`
- `4h Bias: ...`
- Gründe: Liquidity + Golden Zone
- `Warte auf:` CHoCH / 15m B&C / Retest
- TTL

### TRADE Template
- `🟢 [TRADE] Entry freigegeben – SHORT/LONG`
- Bias-Context
- Confirmation konkret (z.B. `✅ 15m Break&Close unter X`)
- Optional Entry/SL/TP

---

## 6) Datenmodell-Erweiterung (ohne Umbau)

### FeatureResult als Events + Meta
```json
{ "type":"fib_zone","side":"bullish","tf":"15m","swing_low":78.12,"swing_high":82.90,
  "zone_low":80.10,"zone_high":80.80,"hit_price":80.55,"strength":70 }
```

```json
{ "type":"liquidity_grab","side":"bearish","tf":"15m","level":82.60,"range_high":82.55,
  "wick_size":0.18,"reclaim_close":true,"strength":80 }
```

```json
{ "type":"structure_break","subtype":"choch","side":"bearish","tf":"15m","broken_level":81.90,
  "close_confirmed":true,"strength":90 }
```

### active_setups State (IDEA → TRADE)
Spalte/Key:
- `user_id, symbol, timeframe, setup_id, side, status, created_at, expires_at, data_json, last_notified_at`

TTL: 6–12 Kerzen (15m) als Start.

---

## 7) Engine Flow (Runner) – Reihenfolge

1) Scan → Module → **Raw Features**  
2) **Bias Resolver** (4h -> 1h -> 15m Context)  
3) **Idea Builder** (Liquidity + Fib → IDEA candidate)  
4) **Confirmation Checker** (CHoCH / B&C / LH+Break)  
5) **Pre-Send Validation** (Sanity + Merge + downgrade)  
6) DB upsert `active_setups`  
7) Telegram: send IDEA/TRADE Templates

---

## 8) Pseudocode (kopierbar)

### A) Decision
```python
idea = liquidity_grab(tf="15m") and fib_golden_zone(tf="15m")
if not idea:
    return NONE

status = "IDEA"
confirmation = (
    choch("15m", close_confirmed=True)
    or break_and_close("15m", key_level="value_zone")
    or lower_high_then_break("15m")
)
if confirmation:
    status = "TRADE"

# Bias routing (downgrade)
if bias_4h == "BEAR" and side == "LONG":
    status = "IDEA"; flags.add("COUNTERTREND")
if bias_4h == "BULL" and side == "SHORT":
    status = "IDEA"; flags.add("COUNTERTREND")

status, features = validate_and_cleanup(status, features)
return status, features, flags
```

### B) FVG Merge
```python
def merge_fvgs(fvgs, overlap_threshold=0.6):
    merged, used = [], set()
    for i, a in enumerate(fvgs):
        if i in used: 
            continue
        merged_this = False
        for j, b in enumerate(fvgs):
            if j <= i or j in used:
                continue
            overlap_low = max(a["low"], b["low"])
            overlap_high = min(a["high"], b["high"])
            overlap = max(0.0, overlap_high - overlap_low)
            min_range = min(a["high"]-a["low"], b["high"]-b["low"])
            ratio = overlap / min_range if min_range > 0 else 0.0
            if ratio >= overlap_threshold:
                merged.append({
                    "side": "mixed",
                    "low": min(a["low"], b["low"]),
                    "high": max(a["high"], b["high"]),
                    "note": "overlap_merged",
                })
                used.update({i, j})
                merged_this = True
                break
        if not merged_this:
            merged.append(a)
    return merged
```

### C) Fib Sanity
```python
def fib_sanity(fib):
    assert fib["zone_low"] < fib["zone_high"]
    lo = min(fib["swing_low"], fib["swing_high"])
    hi = max(fib["swing_low"], fib["swing_high"])
    assert lo <= fib["zone_low"] <= hi
    assert lo <= fib["zone_high"] <= hi
```

---

## 9) Rollout-Plan (damit „davor war besser“ nicht passiert)

### Phase 1 (schnell)
- Bias Resolver + Ausgabe als Kontext
- Fib Labels fixen (support/resistance raus)
- FVG overlap merge

### Phase 2
- Pre-Send Validation (block/downgrade)
- active_setups State + TTL + Upgrade-Flow

### Phase 3
- Update-Messages (IDEA → TRADE Upgrade statt Spam)
- Commands: `/watchlist`, `/onlytrade`, `/setups`

---

## 10) Antwort auf deine Frage „zusätzlich oder zu den anderen?“
✅ **Zusätzlich.**  
Du behältst deine Module, aber packst **Routing + Validation + Messaging** darüber, damit alles konsistent wirkt.
