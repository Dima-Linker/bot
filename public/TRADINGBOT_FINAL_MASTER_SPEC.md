# TRADINGBOT – FINAL MASTER SPEC
Analyse-First · Clean Routing · No Noise

## ZIEL
Ein Trading-System, das NICHT zum Blind-Traden animiert, sondern:
- Märkte vorsortiert
- Relevante Zonen meldet
- Den Trader entscheiden lässt

---

## TELEGRAM STRUKTUR (FORUM TOPICS)

1. 🧠 COMBO | High-Quality  
2. 🟡 IDEA | Watchlist  
3. 📐 FIBONACCI  
4. 💧 LIQUIDITY | SMC  
5. 🔥 PUMP | MOMENTUM  
6. 🧪 TEST | DEBUG  

---

## GRUNDREGEL (KRITISCH)
❌ KEIN Signal darf im falschen Topic landen  
❌ COMBO darf NIE in IDEA erscheinen  

---

## SIGNAL-TYPEN

### 🟡 IDEA | Watchlist
Analyse-Hinweise – kein Trade

Trigger:
- HTF Liquidity Grab
- MACD Struktur
- Bias vorhanden, aber Entry fehlt

Keine Entries, kein TP, kein SL

---

### 📐 FIBONACCI
Heads-up Alerts

Trigger:
- Golden Zone Touch
- ATR-Filter
- Max 2 Touches
- Optional Reclaim Close

---

### 💧 LIQUIDITY | SMC
Smart Money Hinweise

Trigger:
- Equal High/Low Sweep
- Stop Hunt
- Inducement
- Liquidity Void

---

### 🔥 PUMP | MOMENTUM
Scanner für starke Moves

Trigger:
- Preis > +X % in Y Minuten
- Volumen Spike
- Breakout aus Range

---

### 🧠 COMBO | High-Quality
Trade-Kandidaten

Pflicht:
- HTF Bias passt
- SMC + Fib + Momentum
- Score ≥ 300
- Kein Countertrend

---

## ROUTING-LOGIK (FIX FÜR IDEA/COMBO BUG)

```python
if signal.type == "COMBO":
    send_to(COMBO_TOPIC)
elif signal.type == "IDEA":
    send_to(IDEA_TOPIC)
```

KEIN FALL-THROUGH ERLAUBT

---

## SCORE TRENNUNG

| Modul | Max |
|-----|-----|
| Fib | 100 |
| SMC | 100 |
| Momentum | 80 |
| HTF Bias | 60 |
| Entry Confirmation | 60 |

COMBO ≥ 300  
IDEA < 300  

---

## USER FLOW (SO DENKT DER TRADER)

1. 📐 / 💧 → Markt beobachten
2. 🟡 IDEA → Setup baut sich
3. 🧠 COMBO → Trade erlaubt

---

## WARUM DAS SYSTEM JETZT RICHTIG IST

✅ Kein Spam  
✅ Kein Würfeln  
✅ Keine widersprüchlichen Signale  
✅ Fokus auf Analyse  
✅ Trader bleibt Entscheider  

---

## STATUS
System = PRODUKTIONSREIF  
Nur Marktbedingungen bestimmen Alerts

