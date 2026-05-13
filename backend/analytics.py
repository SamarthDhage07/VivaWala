"""
Analytics Module
Uses NumPy for score calculations and Matplotlib for visualizations.
"""

import os
import json
import logging
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

logger = logging.getLogger(__name__)

GRAPHS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "graphs")
os.makedirs(GRAPHS_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# NumPy Analytics
# ──────────────────────────────────────────────

def calculate_analytics(qa_history: list[dict]) -> dict:
    """
    Compute comprehensive analytics from Q&A history using NumPy.
    """
    if not qa_history:
        return {}

    scores = np.array([item.get("score", 0) for item in qa_history], dtype=float)
    n = len(scores)

    # Basic stats
    avg = float(np.mean(scores))
    median = float(np.median(scores))
    std = float(np.std(scores))
    min_score = float(np.min(scores))
    max_score = float(np.max(scores))

    # Trend: positive if improving over time
    if n >= 3:
        x = np.arange(n)
        coeffs = np.polyfit(x, scores, 1)
        trend = "improving" if coeffs[0] > 0.1 else ("declining" if coeffs[0] < -0.1 else "stable")
        trend_slope = float(coeffs[0])
    else:
        trend = "insufficient data"
        trend_slope = 0.0

    # Performance buckets
    excellent = int(np.sum(scores >= 8))
    good = int(np.sum((scores >= 6) & (scores < 8)))
    average = int(np.sum((scores >= 4) & (scores < 6)))
    poor = int(np.sum(scores < 4))

    # Consistency (lower CV = more consistent)
    cv = float(std / avg * 100) if avg > 0 else 0
    consistency = "high" if cv < 20 else ("medium" if cv < 40 else "low")

    # Percentile-like performance rating
    performance_pct = float((avg / 10.0) * 100)

    # Running averages (cumulative mean)
    cumulative_avg = np.cumsum(scores) / np.arange(1, n + 1)

    return {
        "scores": scores.tolist(),
        "average_score": round(avg, 2),
        "median_score": round(median, 2),
        "std_deviation": round(std, 2),
        "min_score": round(min_score, 2),
        "max_score": round(max_score, 2),
        "total_questions": n,
        "trend": trend,
        "trend_slope": round(trend_slope, 3),
        "performance_buckets": {
            "excellent": excellent,
            "good": good,
            "average": average,
            "poor": poor,
        },
        "consistency": consistency,
        "coefficient_of_variation": round(cv, 2),
        "performance_percentage": round(performance_pct, 1),
        "cumulative_averages": [round(float(v), 2) for v in cumulative_avg],
        "grade": _get_grade(avg),
    }


def _get_grade(avg_score: float) -> str:
    if avg_score >= 9:
        return "A+"
    elif avg_score >= 8:
        return "A"
    elif avg_score >= 7:
        return "B+"
    elif avg_score >= 6:
        return "B"
    elif avg_score >= 5:
        return "C"
    elif avg_score >= 4:
        return "D"
    else:
        return "F"


# ──────────────────────────────────────────────
# Matplotlib Visualizations
# ──────────────────────────────────────────────

# Color palette
COLORS = {
    "bg": "#0a0e1a",
    "panel": "#111827",
    "accent": "#00d4ff",
    "accent2": "#7c3aed",
    "green": "#10b981",
    "red": "#ef4444",
    "yellow": "#f59e0b",
    "text": "#e2e8f0",
    "muted": "#64748b",
    "grid": "#1e293b",
}


def _apply_dark_style(fig, axes_list):
    """Apply dark futuristic style to figure."""
    fig.patch.set_facecolor(COLORS["bg"])
    for ax in axes_list:
        ax.set_facecolor(COLORS["panel"])
        ax.tick_params(colors=COLORS["text"], labelsize=9)
        ax.xaxis.label.set_color(COLORS["text"])
        ax.yaxis.label.set_color(COLORS["text"])
        ax.title.set_color(COLORS["accent"])
        for spine in ax.spines.values():
            spine.set_edgecolor(COLORS["grid"])
        ax.grid(color=COLORS["grid"], linestyle="--", alpha=0.5)


def generate_score_progression_graph(
    qa_history: list[dict], domain: str, session_id: str
) -> str:
    """Generate score progression line chart."""
    analytics = calculate_analytics(qa_history)
    scores = analytics["scores"]
    cumulative = analytics["cumulative_averages"]
    n = len(scores)
    x = np.arange(1, n + 1)

    fig, ax = plt.subplots(figsize=(10, 5))
    _apply_dark_style(fig, [ax])

    # Score bars
    bar_colors = [
        COLORS["green"] if s >= 7 else COLORS["yellow"] if s >= 5 else COLORS["red"]
        for s in scores
    ]
    bars = ax.bar(x, scores, color=bar_colors, alpha=0.7, width=0.5, zorder=2)

    # Cumulative average line
    ax.plot(x, cumulative, color=COLORS["accent"], linewidth=2.5,
            marker="o", markersize=6, label="Cumulative Avg", zorder=3)

    # Horizontal threshold lines
    ax.axhline(7, color=COLORS["green"], linestyle=":", alpha=0.5, linewidth=1)
    ax.axhline(5, color=COLORS["yellow"], linestyle=":", alpha=0.5, linewidth=1)

    # Score labels on bars
    for bar, score in zip(bars, scores):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.15,
            f"{score:.0f}",
            ha="center", va="bottom",
            color=COLORS["text"], fontsize=9, fontweight="bold",
        )

    ax.set_xlim(0.3, n + 0.7)
    ax.set_ylim(0, 11)
    ax.set_xticks(x)
    ax.set_xticklabels([f"Q{i}" for i in x])
    ax.set_xlabel("Question Number")
    ax.set_ylabel("Score (0–10)")
    ax.set_title(f"Score Progression — {domain}", fontsize=13, pad=15)
    ax.legend(loc="upper left", facecolor=COLORS["panel"], edgecolor=COLORS["grid"],
              labelcolor=COLORS["text"])

    path = os.path.join(GRAPHS_DIR, f"{session_id}_progression.png")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return path


def generate_performance_pie_chart(
    analytics: dict, domain: str, session_id: str
) -> str:
    """Generate performance distribution donut chart."""
    buckets = analytics.get("performance_buckets", {})
    labels = ["Excellent (8-10)", "Good (6-7)", "Average (4-5)", "Poor (0-3)"]
    sizes = [buckets.get("excellent", 0), buckets.get("good", 0),
             buckets.get("average", 0), buckets.get("poor", 0)]
    colors = [COLORS["green"], COLORS["accent"], COLORS["yellow"], COLORS["red"]]

    # Filter zeros
    filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
    if not filtered:
        return ""
    labels_f, sizes_f, colors_f = zip(*filtered)

    fig, ax = plt.subplots(figsize=(7, 6))
    _apply_dark_style(fig, [ax])

    wedges, texts, autotexts = ax.pie(
        sizes_f,
        labels=labels_f,
        colors=colors_f,
        autopct="%1.0f%%",
        startangle=90,
        pctdistance=0.75,
        wedgeprops={"width": 0.55, "edgecolor": COLORS["bg"], "linewidth": 2},
    )
    for t in texts:
        t.set_color(COLORS["text"])
        t.set_fontsize(10)
    for at in autotexts:
        at.set_color(COLORS["bg"])
        at.set_fontweight("bold")
        at.set_fontsize(10)

    # Center text
    ax.text(0, 0.05, f"{analytics['average_score']:.1f}", ha="center", va="center",
            fontsize=26, fontweight="bold", color=COLORS["accent"])
    ax.text(0, -0.25, analytics["grade"], ha="center", va="center",
            fontsize=14, color=COLORS["text"])

    ax.set_title(f"Answer Quality Distribution — {domain}", fontsize=12, pad=15)
    path = os.path.join(GRAPHS_DIR, f"{session_id}_distribution.png")
    plt.tight_layout()
    plt.savefig(path, dpi=120, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return path


def generate_analytics_dashboard(
    qa_history: list[dict], domain: str, session_id: str
) -> str:
    """
    Generate a comprehensive 2x2 analytics dashboard image.
    Returns the file path.
    """
    analytics = calculate_analytics(qa_history)
    scores = np.array(analytics["scores"])
    cumulative = analytics["cumulative_averages"]
    n = len(scores)
    x = np.arange(1, n + 1)

    fig = plt.figure(figsize=(14, 10))
    fig.patch.set_facecolor(COLORS["bg"])
    gs = GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    # ── Plot 1: Score Progression ──
    ax1 = fig.add_subplot(gs[0, 0])
    _apply_dark_style(fig, [ax1])
    bar_colors = [
        COLORS["green"] if s >= 7 else COLORS["yellow"] if s >= 5 else COLORS["red"]
        for s in scores
    ]
    ax1.bar(x, scores, color=bar_colors, alpha=0.75, width=0.5, zorder=2)
    ax1.plot(x, cumulative, color=COLORS["accent"], linewidth=2,
             marker="o", markersize=5, zorder=3)
    ax1.set_ylim(0, 11)
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Q{i}" for i in x], fontsize=8)
    ax1.set_title("Score Progression", fontsize=11)
    ax1.set_ylabel("Score")

    # ── Plot 2: Strength Radar / Metrics ──
    ax2 = fig.add_subplot(gs[0, 1])
    _apply_dark_style(fig, [ax2])
    metrics = {
        "Avg Score": analytics["average_score"] / 10,
        "Consistency": (1 - min(analytics["coefficient_of_variation"] / 100, 1)),
        "Peak Perf.": analytics["max_score"] / 10,
        "Excellence": analytics["performance_buckets"]["excellent"] / max(n, 1),
    }
    metric_names = list(metrics.keys())
    metric_vals = list(metrics.values())
    bars2 = ax2.barh(metric_names, metric_vals,
                     color=[COLORS["accent"], COLORS["accent2"], COLORS["green"], COLORS["yellow"]],
                     alpha=0.8, height=0.5)
    for bar, val in zip(bars2, metric_vals):
        ax2.text(min(val + 0.02, 0.95), bar.get_y() + bar.get_height() / 2,
                 f"{val*100:.0f}%", va="center", color=COLORS["text"], fontsize=9)
    ax2.set_xlim(0, 1.1)
    ax2.set_title("Performance Metrics", fontsize=11)
    ax2.tick_params(axis="y", labelsize=9)

    # ── Plot 3: Distribution Pie ──
    ax3 = fig.add_subplot(gs[1, 0])
    _apply_dark_style(fig, [ax3])
    buckets = analytics["performance_buckets"]
    pie_data = [("Excellent", buckets["excellent"], COLORS["green"]),
                ("Good", buckets["good"], COLORS["accent"]),
                ("Average", buckets["average"], COLORS["yellow"]),
                ("Poor", buckets["poor"], COLORS["red"])]
    pie_data = [(l, v, c) for l, v, c in pie_data if v > 0]
    if pie_data:
        labels_p, vals_p, colors_p = zip(*pie_data)
        ax3.pie(vals_p, labels=labels_p, colors=colors_p,
                autopct="%1.0f%%", startangle=90,
                wedgeprops={"edgecolor": COLORS["bg"], "linewidth": 2},
                textprops={"color": COLORS["text"], "fontsize": 9})
    ax3.set_title("Answer Distribution", fontsize=11)

    # ── Plot 4: Stats Summary ──
    ax4 = fig.add_subplot(gs[1, 1])
    _apply_dark_style(fig, [ax4])
    ax4.axis("off")
    stats_text = [
        ("Domain", domain),
        ("Total Questions", str(analytics["total_questions"])),
        ("Average Score", f"{analytics['average_score']:.1f} / 10"),
        ("Median Score", f"{analytics['median_score']:.1f} / 10"),
        ("Grade", analytics["grade"]),
        ("Performance", f"{analytics['performance_percentage']:.0f}%"),
        ("Trend", analytics["trend"].capitalize()),
        ("Consistency", analytics["consistency"].capitalize()),
    ]
    y_pos = 0.95
    for key, val in stats_text:
        ax4.text(0.05, y_pos, f"{key}:", transform=ax4.transAxes,
                 fontsize=10, color=COLORS["muted"], va="top")
        ax4.text(0.55, y_pos, val, transform=ax4.transAxes,
                 fontsize=10, color=COLORS["accent"], va="top", fontweight="bold")
        y_pos -= 0.115

    ax4.set_title("Interview Summary", fontsize=11)

    # Title
    fig.suptitle(
        f"AI Interview Analytics Dashboard",
        fontsize=16, color=COLORS["accent"],
        fontweight="bold", y=0.98,
    )

    path = os.path.join(GRAPHS_DIR, f"{session_id}_dashboard.png")
    plt.savefig(path, dpi=120, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    return path
