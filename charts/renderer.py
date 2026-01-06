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
    annotation: dict | None = None, # signal annotation data
) -> str:
    overlays = overlays or {}
    indicators = indicators or {}
    annotation = annotation or {}

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
    
    # Calculate current price for annotations
    current_price = df['Close'].iloc[-1] if not df.empty else 0
    # Light theme style with enhanced candle colors
    mc = mpf.make_marketcolors(up="#22c55e", down="#ef4444", edge="#16a34a", wick="#16a34a", volume="#d1d5db")
    s = mpf.make_mpf_style(
        base_mpf_style="default",
        marketcolors=mc,
        gridstyle="--",
        facecolor="#ffffff",
        figcolor="#ffffff",
        rc={"axes.labelcolor":"#374151","xtick.color":"#6b7280","ytick.color":"#6b7280"}
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
        # Filter out None values and ensure all are floats
        hline_levels = [level for level in overlays["hlevels"] if level is not None]
        hline_levels = [float(level) for level in hline_levels if level is not None and str(level).replace('.', '', 1).isdigit()]

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

    # Create unique filename with timestamp to prevent overwriting
    import time
    timestamp = int(time.time() * 1000)  # Millisecond precision
    file_path = Path(out_dir) / f"{symbol}_{timeframe}_{timestamp}.png"

    # Calculate number of panels based on indicators only (horizontal lines don't create new panels)
    indicator_panels = 0
    if "rsi" in indicators:
        indicator_panels += 1
    if {"macd","signal","hist"} <= set(indicators.keys()):
        indicator_panels += 1
    
    # Total panels = main chart + volume (always added by mplfinance when volume=True) + indicator panels
    # Volume panel is automatically created by mplfinance, so we need to account for it
    total_panels = 1 + 1 + indicator_panels  # main + volume + indicators
    
    # Set panel ratios with more space for main chart (75-80%)
    if total_panels == 2:  # main + volume
        panel_ratios = (75, 25)  # Main chart gets 75%, volume gets 25%
    elif total_panels == 3:  # main + volume + 1 indicator
        panel_ratios = (70, 15, 15)  # Main chart gets 70%, others get 15%
    elif total_panels == 4:  # main + volume + 2 indicators
        panel_ratios = (65, 15, 10, 10)  # Main chart gets 65%, others get 15% and 10%
    else:  # default case (main + volume)
        panel_ratios = (75, 25)  # Main chart gets 75%

    # Build plot arguments
    plot_args = [df]
    plot_kwargs = {
        'type': "candle",
        'volume': True,
        'style': s,
        'title': f"{symbol} • {timeframe}",
        'figsize': (12, 8),  # Larger size for better layout
        'panel_ratios': panel_ratios,
    }
    
    if apds:
        plot_kwargs['addplot'] = apds
    if hlines:
        plot_kwargs['hlines'] = hlines
    if alines:
        plot_kwargs['alines'] = alines
    
    # Add savefig at the end
    plot_kwargs['savefig'] = dict(fname=str(file_path), dpi=170, bbox_inches="tight")
    
    mpf.plot(*plot_args, **plot_kwargs)
    
    # Add annotation overlay using matplotlib if annotation data is provided
    if annotation:
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
        
        # Reopen the saved image to add annotation
        fig, ax = plt.subplots(figsize=(12, 8))
        img = plt.imread(str(file_path))
        ax.imshow(img)
        ax.axis('off')
        
        # Add annotation box to the right side of the image, not blocking candles
        img_height, img_width = img.shape[:2]
        box_width, box_height = img_width * 0.35, img_height * 0.4  # Smaller box
        # Position box on the right side, leaving main chart area clear
        box_x, box_y = img_width * 0.63, (img_height - box_height) / 2
        
        # Determine background color based on direction
        bg_color = '#fee2e2' if annotation.get('direction') == 'short' else '#dcfce7'  # Light red for short, light green for long
        
        # Create annotation box with direction-based background
        rect = Rectangle((box_x, box_y), box_width, box_height, 
                        linewidth=2, edgecolor='#374151', facecolor=bg_color, alpha=0.8)
        ax.add_patch(rect)
        
        # Add annotation text
        annotation_text = []
        if annotation.get('direction'):
            direction_emoji = "🟥 SHORT" if annotation['direction'] == 'short' else "🟩 LONG"
            annotation_text.append(f"{direction_emoji}")
        if annotation.get('score'):
            stars = "⭐" * int(annotation['score'] / 2)  # Convert score to stars
            annotation_text.append(f"Score: {annotation['score']}/10 {stars}")
        if annotation.get('reasons'):
            for reason in annotation['reasons'][:4]:  # Limit to 4 reasons
                annotation_text.append(f"{reason}")
        
        if annotation_text:
            full_text = "\n".join(annotation_text)
            ax.text(box_x + box_width/2, box_y + box_height/2, full_text, 
                   horizontalalignment='center', verticalalignment='center',
                   fontsize=10, fontweight='bold', color='#1f2937')
        
        # Add current price box in top right corner
        if current_price > 0:
            price_text = f"Current: {current_price:.2f} USDT"
            ax.text(img_width - 20, 20, price_text,
                   horizontalalignment='right', verticalalignment='top',
                   fontsize=10, fontweight='bold', color='#1f2937',
                   bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='#374151'))
        
        # Add watermark in bottom left corner
        ax.text(20, img_height - 10, "@CryptoSignalHub",
               horizontalalignment='left', verticalalignment='bottom',
               fontsize=8, fontweight='normal', color='#9ca3af',
               alpha=0.6)
        
        # Add TP/SL lines if provided in annotation
        if 'tp_levels' in annotation or 'sl_level' in annotation:
            # Draw horizontal lines for TP levels
            for i, tp_level in enumerate(annotation.get('tp_levels', [])):
                # Convert price to image coordinate (simplified approach)
                # This is a simplified approach - in a real implementation, you'd need to map price to y-coord
                # For now, just add text labels
                ax.text(img_width - 50, 100 + i*30, f"TP{i+1}: {tp_level:.2f}",
                       horizontalalignment='right', verticalalignment='top',
                       fontsize=10, fontweight='bold', color='green',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='lightgreen', alpha=0.7, edgecolor='green'))
            
            # Draw SL level
            if 'sl_level' in annotation:
                sl_level = annotation['sl_level']
                ax.text(img_width - 50, 160, f"SL: {sl_level:.2f}",
                       horizontalalignment='right', verticalalignment='top',
                       fontsize=10, fontweight='bold', color='red',
                       bbox=dict(boxstyle='round,pad=0.2', facecolor='lightcoral', alpha=0.7, edgecolor='red'))
        
        # Save the annotated image
        plt.savefig(str(file_path), dpi=170, bbox_inches="tight")
        plt.close()

    return str(file_path)