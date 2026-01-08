# 💧 SMC – Liquidity Sweep + Reclaim (Single-Alerts) – Umsetzung (MD)

Ziel: **Pro-Scanner Notifications** für erfahrene Nutzer.  
Der Bot markiert **Liquidity Events** (Stops/Liquidität abgeholt) als **Heads-up** im Topic **💧 LIQUIDITY | SMC**.  
**Kein Entry-Call**, keine „Trade“-Aussage – nur: *„Hier lohnt sich ein Blick“*.

---

## 0) Prinzip: ALERT ≠ IDEA ≠ TRADE

- **LIQUIDITY ALERT (Single):** SMC Event → *Heads-up*, **kein Entry**
- **IDEA:** Liquidity + Fib (Golden Zone) → Watchlist
- **TRADE:** IDEA + Confirmation (CHoCH / Break&Close / LH/HL+Break) → Entry-Freigabe

---

## 1) Telegram Topic Routing

Du hast Topics. Liquidity Alerts gehen **nur** in:

- 💧 `LIQUIDITY | SMC` → `smc_liquidity_alert`

Router-Regel:
- `event.type == "smc_liquidity_alert"` → Topic `SMC`
- `status == IDEA` → Topic `IDEA`
- `status == TRADE` → Topic `COMBO`

**Wichtig:** für Text **und** Bild `message_thread_id` verwenden!

---

## 2) Was ist ein „Liquidity Sweep + Reclaim“?

### 2.1 Definition (objektiv)
Ein Liquidity Sweep besteht aus:

1) **Sweep (Wick bricht ein Liquiditäts-Level)**
2) **Reclaim (Close kommt zurück über/unter das Level)**

👉 Das ist die Kernlogik, die sehr zuverlässig ist und wenig spammt.

---

## 3) Welche Liquidity-Levels erkennt der Bot?

Wir starten bewusst mit 2 robusten Level-Typen:

### A) Equal Highs / Equal Lows (EQH/EQL)
- EQH: mehrere Hochs auf ähnlichem Preis → Sell-Stops darüber
- EQL: mehrere Tiefs auf ähnlichem Preis → Buy-Stops darunter

**Parameter (Startwerte):**
- Lookback: `N = 60` Kerzen (15m) / `N = 80` (1h)
- Mindestanzahl Touches: `>= 2`
- Toleranz: `tol = 0.08% – 0.20%` (abhängig vom Symbol)  
  Alternative: `tol = 0.25 * ATR(14) / price`

### B) Range High / Range Low
- Bestimme Range-High/Low im Lookback-Fenster
- Sweep über Range-High oder unter Range-Low
- Reclaim close zurück in die Range

**Parameter:**
- Lookback: `N = 40–80` Kerzen
- Range muss „stabil“ sein (optional): RangeWidth <= X * ATR

> Hinweis: Du kannst zuerst nur EQH/EQL machen (empfohlen), Range später aktivieren.

---

## 4) Erkennungslogik (Candle Rules)

Wir arbeiten candle-basiert und **close-confirmed**.

### 4.1 Bearish Sweep (liquidity grab oben)
- Preis wick **über** das Level: `high > level + tol`
- Candle schließt **unter**/zurück unter das Level: `close < level - tol_close`

**Reclaim streng vs locker:**
- Streng: `close < level - tol_close`
- Locker: `close <= level`

### 4.2 Bullish Sweep (liquidity grab unten)
- `low < level - tol`
- `close > level + tol_close`

**Empfohlene Startwerte:**
- `tol_close = tol * 0.5` (oder minimal 0.02%)

---

## 5) Quality Filter (damit es Pro bleibt und nicht spammt)

### 5.1 Wick/ATR Signifikanz (Pflicht)
Sende nur, wenn der Sweep “wirklich” ist:

- `wick_size >= 0.6 * ATR(14)` **oder**
- `candle_range >= 0.9 * ATR(14)`

### 5.2 Reclaim Qualität
- Bonus, wenn reclaim eindeutig ist:
  - bearish: close deutlich unter level
  - bullish: close deutlich über level

### 5.3 Abstand zur aktuellen Price-Zone (optional)
- Wenn Level extrem weit weg ist → skip
- aber bei Sweep ist es meist nahe.

### 5.4 Touch Count Filter
- EQH/EQL müssen vorher „echte“ Liquidity sein:
  - mindestens 2 Touches innerhalb tol

---

## 6) Scoring (0–100) für Liquidity Alert

Ziel: nicht „Trade Score“, sondern “wie interessant ist das”.

**Vorschlag:**
- Level Type:
  - EQH/EQL = +35
  - Range High/Low = +25
- Sweep Strength:
  - wick_size / ATR >= 0.6 → +20
  - wick_size / ATR >= 1.0 → +30 (statt +20)
- Reclaim Close:
  - klarer reclaim (close beyond tol_close) = +20
  - nur knapp = +10
- Touch Count:
  - 2 touches = +10
  - 3+ touches = +15

**Threshold:**
- send only if `score >= 60` (Testing: 40)

---

## 7) Datenmodell (Event / Feature)

Beispiel:
```json
{
  "type": "smc_liquidity_alert",
  "side": "bearish",
  "tf": "15m",
  "symbol": "BTCUSDT",
  "level_type": "EQH",
  "level": 94250.0,
  "tol": 20.0,
  "sweep_high": 94340.0,
  "reclaim_close": true,
  "atr14": 120.0,
  "wick_size": 150.0,
  "touch_count": 3,
  "score": 78,
  "created_at": "2026-01-07T10:00:00Z"
}
```

---

## 8) DB / Cooldown / Dedup

### 8.1 Fingerprint (Dedup)
```
smc_liq:{symbol}:{tf}:{side}:{level_type}:{level}
```

### 8.2 Cooldowns (Startwerte)
- 15m: 90 Minuten
- 1h: 4 Stunden
- 4h: 12 Stunden (optional später)

👉 Cooldown nur für `smc_liquidity_alert`, getrennt von IDEA/TRADE.

---

## 9) Telegram Message Template (DE, Heads-up)

**Kurz, klar, kein Entry:**

```
💧 LIQUIDITY ALERT (Heads-up)
🪙 {symbol} | TF: {tf} | 4h Bias: {bias_4h}

Event: {level_type} Sweep + Reclaim {reclaim_emoji}
Level: {level}
Wick: {wick_size:.2f} | ATR(14): {atr14:.2f}
Touches: {touch_count}
Qualität: {score}/100

Hinweis:
→ Kein Entry-Signal. Beobachte CHoCH / Break&Close / Retest.
```

**reclaim_emoji:**
- `✅` wenn reclaim_close True
- `⚠️` wenn nur touch/sweep ohne sauberen reclaim (optional – normalerweise skip)

---

## 10) Chart Overlay (minimal)
Für Liquidity Alerts reicht:
- horizontale Linie auf `level`
- Markierung der Sweep-Kerze (Punkt/Label „Sweep“)
- kleine Box rechts: `Liquidity Alert + Score`

---

## 11) Pseudocode (Einbau in deinen Flow)

```python
event = smc_module.detect_liquidity_alert(candles, symbol, tf)

if event and event.score >= THRESHOLD:
    if not cooldown.active(event.fingerprint):
        send(topic="SMC", text=build_liq_msg(event), chart=render_chart(event))
        cooldown.mark(event.fingerprint)
```

---

## 12) Empfohlene Defaults (Start)
- TFs: `15m` + `1h` (4h später)
- Threshold: 60 (Testing 40)
- Nur EQH/EQL zuerst (Range optional später)
- Cooldown: 90m (15m), 4h (1h)

---

## 13) Ergebnis: Was wird dadurch besser?
- Du bekommst **extrem nützliche “Stops geholt” Heads-ups**
- sehr wenig Spam durch ATR/Wick Filter
- perfekt für erfahrene Nutzer (du schaust rein und entscheidest selbst)
- saubere Telegram UX: alles im 💧 Topic

---

## 14) Nächster Schritt (nach Liquidity)
Wenn das stabil läuft, erweitern wir kontrolliert:
1) 🕳️ FVG Alerts (nur große + nah am Preis + overlap merge)
2) 🧱 Order Blocks (nur mitigated + nahe + rejection)
3) IDEA → TRADE Upgrade mit Struktur-Bestätigung
