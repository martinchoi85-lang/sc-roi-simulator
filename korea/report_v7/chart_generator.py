"""Generates high-resolution chart images for PPT report slides using matplotlib and LGE Palette.

Output Assets:
1. slide6_peak_profiles.png: 3-house peak day 15-minute load, PV, and ESS operation.
2. slide7_critical_window.png: 15-day critical day window (GHI, Load, PV, ESS, SoC).
3. slide9_zerobill_ranges.png: Zero Bill Low / Central / High CAPEX comparison bars.
"""

from pathlib import Path
import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# Set matplotlib backend to Agg
plt.switch_backend("Agg")

# LGE Color Palette Tokens
LGE_RED = "#A50034"
LGE_ACTIVE_RED = "#FD312E"
LGE_DARK = "#000000"
LGE_GRAY = "#707070"
LGE_WARM_GRAY = "#F0ECE4"
WHITE = "#FFFFFF"

# Configure Korean font support
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def generate_all_charts(report_data: dict, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Chart 1: Slide 6 - 3 Houses Peak Day Profiles (3 subplots side-by-side)
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8), dpi=200, sharey=True)
    house_keys = ["MONO Core 54", "MONO Core 72", "DUO Max 45"]

    times_96 = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 15, 30, 45)]
    x_indices = np.arange(96)
    x_ticks = np.arange(0, 96, 16)  # Every 4 hours: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00
    x_labels = [times_96[i] for i in x_ticks]

    for idx, hm in enumerate(house_keys):
        ax = axes[idx]
        prof = report_data["peak_day_profiles"].get(hm, {})
        load_kw = prof.get("load_kw", [])
        pv_kw = prof.get("pv_kw", [])
        ess_net_kw = prof.get("ess_net_kw", [])
        pv_sz = prof.get("actual_pv_kw", 0.0)
        ess_sz = prof.get("actual_ess_kwh", 0.0)

        ax.plot(x_indices, load_kw, label="부하 (Load)", color=LGE_DARK, linewidth=2.0)
        ax.plot(x_indices, pv_kw, label=f"PV 발전 ({pv_sz:.2f}kW)", color=LGE_RED, linewidth=2.0)
        ax.plot(x_indices, ess_net_kw, label="ESS 충방전 (Net)", color=LGE_GRAY, linewidth=1.5, linestyle="--")

        ax.set_title(f"{hm}\n(AWHP, EV 0, PV {pv_sz:.2f}kW, ESS {ess_sz:.1f}kWh)", fontsize=11, fontweight="bold", pad=8)
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels, fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.6, color="#CCCCCC")
        ax.set_xlabel("시각 (Time)", fontsize=10)
        if idx == 0:
            ax.set_ylabel("전력 (kW)", fontsize=10)
            ax.legend(loc="upper right", fontsize=8.5, framealpha=0.9)

    plt.tight_layout()
    chart1_path = output_dir / "slide6_peak_profiles.png"
    plt.savefig(chart1_path, bbox_inches="tight")
    plt.close()

    # -------------------------------------------------------------------------
    # Chart 2: Slide 7 - Critical Day Window (Top: Daily GHI, Bottom: 15-min series)
    # -------------------------------------------------------------------------
    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 5.2), dpi=200, gridspec_kw={"height_ratios": [1, 1.4]})

    # Top: Daily GHI bars for 15 days
    daily_list = report_data.get("critical_window_daily", [])
    dates_short = [d["date"][5:] for d in daily_list]  # MM-DD
    ghis = [d["ghi_kwh_m2"] for d in daily_list]
    bar_colors = [LGE_ACTIVE_RED if d.get("is_critical") else LGE_GRAY for d in daily_list]

    bars = ax_top.bar(dates_short, ghis, color=bar_colors, width=0.6, edgecolor=LGE_DARK, linewidth=0.5)
    ax_top.set_title("Critical Day (2026-02-03) 전후 7일 일별 일사량 (Daily GHI)", fontsize=11, fontweight="bold", pad=6)
    ax_top.set_ylabel("GHI (kWh/m²)", fontsize=10)
    ax_top.grid(True, linestyle=":", alpha=0.5, axis="y")
    ax_top.tick_params(axis="x", labelsize=9)

    for bar, ghi in zip(bars, ghis):
        y_val = bar.get_height()
        ax_top.text(bar.get_x() + bar.get_width() / 2, y_val + 0.08, f"{ghi:.2f}", ha="center", va="bottom", fontsize=8)

    # Bottom: 15-min / hourly sampled series for MONO Core 54
    crit_15m = report_data.get("critical_window_15min", {})
    ts_cnt = len(crit_15m.get("load_kw", []))
    if ts_cnt > 0:
        x_pts = np.arange(ts_cnt)
        ax_bot.plot(x_pts, crit_15m["load_kw"], label="부하 (kW)", color=LGE_DARK, linewidth=1.2)
        ax_bot.plot(x_pts, crit_15m["pv_kw_series"], label=f"PV 발전 ({crit_15m.get('pv_kw', 0)}kW, 감쇄적용)", color=LGE_RED, linewidth=1.2)
        ax_bot.plot(x_pts, crit_15m["soc_pct"], label="ESS SoC (%)", color=LGE_ACTIVE_RED, linewidth=1.5, linestyle=":")

        ax_bot.set_title("15일간 시계열 변화 (MONO Core 54 Zero Energy 기준)", fontsize=11, fontweight="bold", pad=6)
        ax_bot.set_ylabel("kW / SoC(%)", fontsize=10)
        ax_bot.grid(True, linestyle=":", alpha=0.5)
        # 15 days = 360 points (sampled every 1h, 24 pts per day)
        tick_pos = np.arange(12, ts_cnt, 24)
        ax_bot.set_xticks(tick_pos)
        ax_bot.set_xticklabels(dates_short[:len(tick_pos)], fontsize=8.5)
        ax_bot.legend(loc="upper right", fontsize=8.5, framealpha=0.9, ncol=3)

    plt.tight_layout()
    chart2_path = output_dir / "slide7_critical_window.png"
    plt.savefig(chart2_path, bbox_inches="tight")
    plt.close()

    # -------------------------------------------------------------------------
    # Chart 3: Slide 9 - Zero Bill Low / Central / High CAPEX Comparison Bars
    # -------------------------------------------------------------------------
    zb_details = report_data.get("zero_bill_details", [])
    if zb_details:
        fig, ax = plt.subplots(figsize=(13, 4.8), dpi=200)

        labels = [f"{d['house_model']}\n({d['heating_package']})" for d in zb_details]
        lows = [d["capex_low_krw"] / 10000.0 for d in zb_details]        # 만원 단위
        centrals = [d["capex_central_krw"] / 10000.0 for d in zb_details]
        highs = [d["capex_high_krw"] / 10000.0 for d in zb_details]

        x = np.arange(len(labels))
        width = 0.25

        rects1 = ax.bar(x - width, lows, width, label="Low ($283/kWh)", color=LGE_GRAY, edgecolor=LGE_DARK, linewidth=0.5)
        rects2 = ax.bar(x, centrals, width, label="Central ($1,268/kWh)", color=LGE_RED, edgecolor=LGE_DARK, linewidth=0.5)
        rects3 = ax.bar(x + width, highs, width, label="High ($1,337/kWh)", color=LGE_ACTIVE_RED, edgecolor=LGE_DARK, linewidth=0.5)

        ax.set_ylabel("초기 투자비 (만원, VAT/시공비 포함)", fontsize=10)
        ax.set_title("Zero Bill 모델 주택×난방별 ESS 단가 시나리오별 CAPEX 비교 (100% 이용률, 무보조)", fontsize=11, fontweight="bold", pad=8)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=9.5)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.5, axis="y")

        # Format y-axis with comma
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))

        plt.tight_layout()
        chart3_path = output_dir / "slide9_zerobill_ranges.png"
        plt.savefig(chart3_path, bbox_inches="tight")
        plt.close()

    print(f"Generated all charts in {output_dir}")

