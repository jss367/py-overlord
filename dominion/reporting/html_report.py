"""Utility functions for generating HTML reports."""

from __future__ import annotations

import base64
import io
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import binomtest


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert a matplotlib figure to a base64 encoded PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def generate_html_report(results: dict, output_path: Path) -> None:
    """Create an HTML report summarizing battle results."""

    sns.set_theme(style="whitegrid")

    strat1 = results["strategy1_name"]
    strat2 = results["strategy2_name"]

    turns1 = [
        g["turns"]
        for g in results["detailed_results"]
        if g["winner"] == strat1
    ]
    turns2 = [
        g["turns"]
        for g in results["detailed_results"]
        if g["winner"] == strat2
    ]

    margin1 = [
        g["margin"]
        for g in results["detailed_results"]
        if g["winner"] == strat1
    ]
    margin2 = [
        g["margin"]
        for g in results["detailed_results"]
        if g["winner"] == strat2
    ]

    game_numbers = [g["game_number"] for g in results["detailed_results"]]
    margins = [g["margin"] for g in results["detailed_results"]]
    winners = [g["winner"] for g in results["detailed_results"]]

    # Statistical significance of win difference
    win_p = binomtest(
        results["strategy1_wins"],
        results["strategy1_wins"] + results["strategy2_wins"],
        p=0.5,
        alternative="two-sided",
    ).pvalue
    confidence = 1 - win_p

    # Histogram of turns taken when each strategy wins
    fig1, ax1 = plt.subplots()
    bins = range(min(turns1 + turns2), max(turns1 + turns2) + 2)
    sns.histplot(turns1, bins=bins, alpha=0.6, label=strat1, ax=ax1)
    sns.histplot(turns2, bins=bins, alpha=0.6, label=strat2, ax=ax1)
    ax1.set_xlabel("Turns to finish")
    ax1.set_ylabel("Games")
    ax1.set_title("Game length when each strategy wins")
    ax1.legend()
    turn_hist = fig_to_base64(fig1)
    plt.close(fig1)

    # Bar chart of overall wins
    fig2, ax2 = plt.subplots()
    sns.barplot(x=[strat1, strat2], y=[results["strategy1_wins"], results["strategy2_wins"]], ax=ax2)
    ax2.set_ylabel("Wins")
    ax2.set_title("Total Wins")
    win_bar = fig_to_base64(fig2)
    plt.close(fig2)

    # Histogram of victory margin
    fig3, ax3 = plt.subplots()
    if margin1 and margin2:
        margin_bins = range(0, max(margin1 + margin2) + 2)
    else:
        margin_bins = range(0, 2)
    sns.histplot(margin1, bins=margin_bins, alpha=0.6, label=strat1, ax=ax3)
    sns.histplot(margin2, bins=margin_bins, alpha=0.6, label=strat2, ax=ax3)
    ax3.set_xlabel("Victory Margin")
    ax3.set_ylabel("Games")
    ax3.set_title("Margin of Victory")
    ax3.legend()
    margin_hist = fig_to_base64(fig3)
    plt.close(fig3)

    # Margin of victory by game number
    fig4, ax4 = plt.subplots()
    sns.scatterplot(x=game_numbers, y=margins, hue=winners, ax=ax4)
    ax4.set_xlabel("Game Number")
    ax4.set_ylabel("Margin of Victory")
    ax4.set_title("Margin by Game")
    margin_scatter = fig_to_base64(fig4)
    plt.close(fig4)

    html = f"""
    <html>
    <head>
        <title>Skulk Strategy Comparison</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ text-align: center; }}
            img {{ max-width: 800px; display: block; margin: 20px auto; }}
        </style>
    </head>
    <body>
    <h1>Skulk Strategy Comparison</h1>
    <p>Games played: {results['games_played']}</p>
    <p>Confidence the win-rate difference is real: {confidence:.1%} (p={win_p:.4f})</p>
    <h2>Win Counts</h2>
    <img src="data:image/png;base64,{win_bar}" />
    <h2>Game Length (Turns)</h2>
    <img src="data:image/png;base64,{turn_hist}" />
    <h2>Margin of Victory</h2>
    <img src="data:image/png;base64,{margin_hist}" />
    <h2>Margin by Game</h2>
    <img src="data:image/png;base64,{margin_scatter}" />
    </body>
    </html>
    """

    output_path.write_text(html)
    print(f"Report written to {output_path}")
