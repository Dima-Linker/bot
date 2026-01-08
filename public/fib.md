# 📐 Fibonacci Single-Alerts (Telegram Topic) – Erweiterung (MD)

Ziel: Du bekommst **FIB-only Heads-up Signale** (kein Entry-Call), damit du **nicht 500 Coins selbst suchen** musst.  
Diese Alerts landen **nur** im Topic **📐 FIBONACCI** und sind **separat** von `IDEA` (Watchlist) und `COMBO/TRADE`.

---

## 0) Prinzip: ALERT ≠ IDEA ≠ TRADE

- **FIB ALERT (Single):** *Ein* Modul feuert → **Heads-up**, **kein Entry**
- **IDEA:** Liquidity + Fib → Setup-Kandidat (Watchlist)
- **TRADE:** IDEA + Confirmation (CHoCH / Break&Close / LH+Break) → Entry-Freigabe

**Wichtig:** FIB ALERT darf **nicht** wie „High-Quality Setup“ wirken.

---

## 1) Telegram Topic Routing (Fix für Ordnung)

Du brauchst pro Topic eine feste `message_thread_id` (Telegram Forum Topics).

- 📐 `FIBONACCI` → **nur FIB ALERT**
- 🟡 `IDEA | Watchlist` → IDEA
- 🧠 `COMBO | High-Quality` → TRADE

**Router-Regel (kurz):**
- `status == TRADE` → COMBO Topic  
- `status == IDEA` → IDEA Topic  
- `event == FIB_ALERT` → FIB Topic

---

## 2) Was ist ein „FIB ALERT“?

Ein FIB ALERT entsteht, wenn der Kurs **eine Fib-Zone berührt** (oder reclaimt) – **mit Qualität**.

### 2.1 Zonen (empfohlen)
- **Golden Zone:** `0.618 – 0.786` (Hauptzone)
- Optional: `0.5` als weaker zone (standardmäßig aus)

### 2.2 Richtung (Side)
- **bullish**: Pullback in up-swing (wir erwarten Bounce)
- **bearish**: Retrace in down-swing (wir erwarten Reject)

> **Labeling-Fix:** Nie mehr „golden support/resistance“.
> Stattdessen **immer**:
- `Golden Zone Pullback (0.618–0.786)` (bullish)
- `Golden Zone Retrace (0.618–0.786)` (bearish)

---

## 3) Swing-Definition (damit es konsistent bleibt)

Dein häufigster Bug ist: Swing-High/Low vertauscht oder gemischt.  
Darum: **ein** Swing pro TF, klar definiert.

### 3.1 Minimal robuste Swing-Regel (pragmatisch)
1. Nimm die letzten `N=80–140` Kerzen (z.B. 15m: 120 Kerzen).
2. Finde Pivot-High/Pivot-Low (z.B. fractal: 2 links, 2 rechts).
3. Nimm den **letzten bestätigten** Pivot-High und Pivot-Low als Swing-Paar:
   - bullish swing: `swing_low` vor `swing_high`
   - bearish swing: `swing_high` vor `swing_low`

### 3.2 Ein Swing pro Alert
- Speichere `swing_low_time, swing_high_time` (oder Index), damit du *nicht* mehrere Swings durcheinander wirfst.
- Wenn du mehrere Kandidaten findest → nimm den **letzten** (zeitlich jüngsten) validen Swing.

---

## 4) Trigger-Logik (wann senden?)

### 4.1 „Zone Hit“ (Basis)
Ein Hit zählt, wenn:
- `low <= zone_high AND high >= zone_low` (Kerze berührt Zone)

**Quality Upgrade (empfohlen):**
- `close` ist **in** der Zone ODER
- `reclaim`: wick in Zone, **close außerhalb** in erwarteter Richtung  
  - bullish reclaim: wick in zone, close **über** zone_high  
  - bearish reclaim: wick in zone, close **unter** zone_low

### 4.2 Gatekeeping (Anti-Spam)
Sende FIB ALERT nur, wenn zusätzlich:

1) **ATR-Filter**: Candle range oder wick-size ist „signifikant“  
   - z.B. `candle_range >= 0.8 * ATR(14)` **oder** `wick_size >= 0.6 * ATR(14)`

2) **Distance Filter**: Preis war vorher nicht „ewig“ in der Zone  
   - z.B. in den letzten 10 Kerzen: `touch_count <= 2`

3) **Cooldown pro Symbol+TF**:  
   - 15m: 90 Minuten  
   - 1h: 4 Stunden  
   - 4h: 12 Stunden

---

## 5) Scoring (leicht & sinnvoll)

Du willst: *FIB ALERT ist ein Hinweis*, aber trotzdem „Qualität“.

### 5.1 Score-Vorschlag (0–100)
- Zone: Golden Zone = +35
- Reclaim Close (statt nur touch) = +25
- Wick/ATR Signifikanz = +15
- Confluence (optional, ohne andere Module zu „ziehen“):
  - nahe an Key Level (Swing High/Low, SR) = +10
  - VPVR High Volume Node Nähe = +10 (falls vorhanden)

**Sendeschwelle:**
- FIB ALERT senden ab `score >= 60`

---

## 6) Datenmodell (FeatureResult / Event)

Beispiel Event:
```json
{
  "type": "fib_alert",
  "side": "bearish",
  "tf": "15m",
  "symbol": "BCHUSDT",
  "swing_low": 610.2,
  "swing_high": 655.4,
  "zone_low": 642.1,
  "zone_high": 646.0,
  "hit_price": 644.3,
  "hit_kind": "reclaim_close",
  "atr14": 3.2,
  "score": 72,
  "created_at": "2026-01-06T21:00:00Z",
  "meta": {
    "touch_count_10": 1,
    "wick_size": 2.4
  }
}
```

---

## 7) DB / Cooldown (damit du nicht doppelt sendest)

### 7.1 Tabelle `sent_signals` erweitern (oder eigene)
Du brauchst pro Alert mindestens:
- `symbol`
- `timeframe`
- `signal_type` = `fib_alert`
- `side`
- `sent_at`
- `fingerprint` (Hash aus symbol+tf+side+zone+swings)

### 7.2 Fingerprint Beispiel
```
fib_alert:{symbol}:{tf}:{side}:{swing_low}:{swing_high}:{zone_low}:{zone_high}
```

---

## 8) Telegram Message Template (FIB Topic)

**Kurz, klar, kein Entry!**

### 8.1 Standard (DE)
```
📐 FIB ALERT
🪙 {symbol} | TF: {tf} | 4h Bias: {bias_4h}

Event: {label} (0.618–0.786)
Zone: {zone_low} – {zone_high}
Preis: {last_price}
Swing: L={swing_low} / H={swing_high}
Qualität: {score}/100

Hinweis:
→ Heads-up, kein Entry. Warte auf CHoCH / Break&Close / Retest.
```

### 8.2 Optional Zusatz (wenn reclaim)
- `✅ Reclaim Close bestätigt`

---

## 9) Pre-Send Validation (damit nichts „komisch“ wirkt)

Vor Versand prüfen:

1) **Zone-Validität**
- `zone_low < zone_high`
- zone liegt zwischen swing_low und swing_high (korrekter Bereich)

2) **Side Konsistenz**
- bullish → swing_low < swing_high
- bearish → swing_high > swing_low (aber Reihenfolge/zeitliche Lage beachten)

3) **HTF Bias Kontext**
- Wenn `4h bias` hart entgegengesetzt → Label als:
  - `Countertrend Fib Alert` (optional) oder Score -10

4) **Dedupe**
- wenn fingerprint schon gesendet und cooldown aktiv → skip

---

## 10) Pseudocode (Einbau in deinen Flow)

```python
# in scanner loop: pro symbol, pro tf

fib_event = fib_module.detect_fib_alert(candles, tf, symbol)

if fib_event and fib_event.score >= 60:
    if not cooldown.is_active(symbol, tf, "fib_alert", fib_event.fingerprint):
        telegram.send(
            topic="FIBONACCI",
            text=render_fib_alert_message(fib_event, bias_4h),
            chart=render_chart_with_fib_zone(fib_event)
        )
        cooldown.mark_sent(...)
```

---

## 11) Chart Overlay (minimal)
Für FIB-only Chart reicht:
- Zone als transparentes Band (zone_low–zone_high)
- Swing High/Low Linien (optional)
- kleine Box rechts: „FIB ALERT + Zone + Score“

---

## 12) Empfohlene Defaults (Startwerte)
- TFs für FIB Alerts: `15m` und `1h` (4h optional später)
- Cooldown: `15m=90m`, `1h=4h`
- Score threshold: `>= 60`
- Touch gating: `touch_count_10 <= 2`
- Reclaim bevorzugt: `+25 Punkte`

---

## 13) Ergebnis: Was wird dadurch besser?
- Du bekommst **saubere Fib-Hinweise** ohne Entry-Spam.
- Du siehst sofort im **📐 FIBONACCI Topic**, wo „Fib touched“ passiert.
- `IDEA` und `COMBO` bleiben sauber und wirken „pro“ (keine Vermischung).

---

## 14) Nächster Schritt (wenn du willst)
- Ich kann dir danach das gleiche als MD machen für:
  - 💧 Liquidity/SMC Alerts
  - 🚀 Pump/Momentum Alerts
  - oder die gemeinsame Router-/Cooldown-Engine (Option A komplett)
