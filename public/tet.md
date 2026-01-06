Ja, ich sehe genau was du meinst. Du hast jetzt schon dark TradingView-look + Bild, aber:

Kerzen wirken “verkehrt rum” (meist Daten-Reihenfolge falsch)

Linien/Boxen fehlen (Fibo/OB/FVG/RSI/MACD Overlay/Panel noch nicht gezeichnet)

Du willst den Stil wie im Screenshot: Candles + Indikator-Panels + eingezeichnete Zonen/Linien – aber in deinem dunklen Theme.

Hier ist der konkrete Fix-Plan + Code, der in dein Setup passt.

1) Kerzen “verkehrt rum” fixen (99%: Candles nicht sortiert)

Viele Exchanges liefern Klines neuste zuerst. mplfinance erwartet aber chronologisch aufsteigend.

✅ In deinem render_chart_png() direkt nach dem DataFrame-Build:

df = pd.DataFrame(candles)

# sicherstellen: Zahlen sind floats
for col in ["open","high","low","close","volume","ts"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# sortieren (wichtig!)
df = df.sort_values("ts")

df["Date"] = pd.to_datetime(df["ts"], unit="ms")
df = df.set_index("Date")
df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})


Symptom wenn’s falsch ist: Chart “springt” komisch oder wirkt rückwärts.

2) “Weiße Linien” wie im Screenshot einzeichnen

In mplfinance gibt’s 2 saubere Wege:

A) Horizontale Linien (Fibo-Zone, Orderblock Grenzen)

Mit hlines:

hlines = dict(
    hlines=[zone_low, zone_high],   # z.B. fibo golden zone
    colors=["white", "white"],
    linestyle="--",
    linewidths=1,
    alpha=0.9
)

B) Trend-/Divergenz-Linien (schräg)

Mit alines:

alines = dict(
    alines=[ [(t1, p1), (t2, p2)] ],   # t1/t2 müssen datetime sein (Index)
    colors=["white"],
    linestyle="-",
    linewidths=1,
    alpha=0.9
)


Wichtig: t1 und t2 sind df.index[...], nicht unix-ts.

3) RSI/MACD Panels wie im Screenshot (unter den Candles)

Das geht mit mpf.make_addplot().

Beispiel: RSI Panel + RSI(35/70) Lines
import mplfinance as mpf

apds = []

apds.append(mpf.make_addplot(df["RSI"], panel=1, ylabel="RSI", linewidth=1))
apds.append(mpf.make_addplot([35]*len(df), panel=1, linestyle="--", width=1))
apds.append(mpf.make_addplot([70]*len(df), panel=1, linestyle="--", width=1))

Beispiel: MACD Panel
apds.append(mpf.make_addplot(df["MACD"], panel=2, ylabel="MACD", linewidth=1))
apds.append(mpf.make_addplot(df["SIGNAL"], panel=2, linewidth=1))
apds.append(mpf.make_addplot(df["HIST"], panel=2, type="bar", alpha=0.5))


Dann in mpf.plot(..., addplot=apds, panel_ratios=(6,2,2))

4) Konkreter Renderer (fertig) – Candles + Volume + Fibo Zone + optional RSI/MACD

So kannst du dein bestehendes charts/renderer.py upgraden, ohne dein System zu zerlegen:

from __future__ import annotations
from pathlib import Path
import pandas as pd
import mplfinance as mpf

def render_chart_png(
    symbol: str,
    timeframe: str,
    candles: list[dict],
    out_dir: str = "data/charts",
    overlays: dict | None = None,   # fib/ob/fvg/lines
    indicators: dict | None = None, # rsi/macd series
) -> str:
    overlays = overlays or {}
    indicators = indicators or {}

    Path(out_dir).mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(candles)
    for col in ["open","high","low","close","volume","ts"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # KRITISCH: sortieren!
    df = df.sort_values("ts")
    df["Date"] = pd.to_datetime(df["ts"], unit="ms")
    df = df.set_index("Date")
    df = df.rename(columns={"open":"Open","high":"High","low":"Low","close":"Close","volume":"Volume"})
    df = df.tail(140)

    # Dark style
    mc = mpf.make_marketcolors(up="#22c55e", down="#ef4444", edge="inherit", wick="inherit", volume="inherit")
    s = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        gridstyle="--",
        facecolor="#0b1220",
        figcolor="#0b1220",
        rc={"axes.labelcolor":"white","xtick.color":"white","ytick.color":"white"}
    )

    apds = []

    # optional RSI
    if "rsi" in indicators:
        rsi = indicators["rsi"].tail(len(df))
        apds.append(mpf.make_addplot(rsi, panel=1, ylabel="RSI", linewidth=1))
        apds.append(mpf.make_addplot([35]*len(df), panel=1, linestyle="--", width=1))
        apds.append(mpf.make_addplot([70]*len(df), panel=1, linestyle="--", width=1))

    # optional MACD
    if {"macd","signal","hist"} <= set(indicators.keys()):
        macd = indicators["macd"].tail(len(df))
        sig  = indicators["signal"].tail(len(df))
        hist = indicators["hist"].tail(len(df))
        apds.append(mpf.make_addplot(macd, panel=2, ylabel="MACD", linewidth=1))
        apds.append(mpf.make_addplot(sig, panel=2, linewidth=1))
        apds.append(mpf.make_addplot(hist, panel=2, type="bar", alpha=0.5))

    # Linien (weiß) – z.B. fib zone / orderblock
    hline_levels = []
    if "hlevels" in overlays:
        hline_levels = overlays["hlevels"]  # list[float]

    hlines = None
    if hline_levels:
        hlines = dict(
            hlines=hline_levels,
            colors=["white"] * len(hline_levels),
            linestyle="--",
            linewidths=1,
            alpha=0.9,
        )

    # Schräglinien (divergence etc.)
    alines = None
    if "alines" in overlays:
        # overlays["alines"] = [ [(dt1, p1), (dt2, p2)], ... ]
        alines = dict(
            alines=overlays["alines"],
            colors=["white"] * len(overlays["alines"]),
            linestyle="-",
            linewidths=1,
            alpha=0.9,
        )

    file_path = Path(out_dir) / f"{symbol}_{timeframe}.png"

    panels = 1 + (1 if "rsi" in indicators else 0) + (1 if {"macd","signal","hist"} <= set(indicators.keys()) else 0)
    panel_ratios = (6, 2, 2) if panels == 3 else ((6, 2) if panels == 2 else (6,))

    mpf.plot(
        df,
        type="candle",
        volume=True,
        style=s,
        title=f"{symbol} • {timeframe}",
        figsize=(10, 6),
        addplot=apds if apds else None,
        panel_ratios=panel_ratios,
        hlines=hlines,
        alines=alines,
        savefig=dict(fname=str(file_path), dpi=170, bbox_inches="tight"),
    )

    return str(file_path)

5) Wie du deine Zonen aus Modulen in overlays reinreichst

Beispiel Fibo Golden Zone:

overlays = {"hlevels": [fib_618, fib_786]}


Order Block:

overlays = {"hlevels": [ob_low, ob_high]}


Divergence-Linie (weiß):

dt1 = df.index[-50]; dt2 = df.index[-10]
overlays = {"alines": [[(dt1, p1), (dt2, p2)]]}

6) Was wir als Nächstes tun sollten

Damit es exakt wie dein Screenshot wird, brauchen wir die Datenformate aus deinen Modulen:

Fibonacci: Welche Werte speicherst du in FeatureResult.levels? (z.B. {"618":..., "786":...}?)

SMC: Ob Low/High, FVG Low/High in levels?

RSI/MACD: hast du die Serien schon (arrays), oder berechnest du sie nur „ja/nein“?

Wenn du mir ein Beispiel-FeatureResult aus:

fibonacci

smc

macd
(als print(fr.to_dict())) hier rein kopierst, mappe ich dir das sofort so, dass:

Fibo Zone als weiße Linien

Orderblock/FVG als Box (kann man auch machen)

MACD/RSI Panels unten

Dann hast du wirklich 1:1 TradingView-Style in Dark, wie in deinen Screenshots.