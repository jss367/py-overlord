"""Utility functions for generating HTML reports."""

from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import MaxNLocator
from scipy.stats import binomtest


def fig_to_base64(fig: plt.Figure) -> str:
    """Convert a matplotlib figure to a base64 encoded PNG."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def generate_html_report(results: dict, output_path: Path, *, verbose: bool = False) -> None:
    """Create an HTML report summarizing battle results.

    Parameters:
        results: The results dict from a StrategyBattle.
        output_path: Where to write the HTML file.
        verbose: If True, print a confirmation message to stdout.
    """

    sns.set_theme(style="whitegrid")

    strat1 = results["strategy1_name"]
    strat2 = results["strategy2_name"]

    turns1 = [g["turns"] for g in results["detailed_results"] if g["winner"] == strat1]
    turns2 = [g["turns"] for g in results["detailed_results"] if g["winner"] == strat2]

    margin1 = [g["margin"] for g in results["detailed_results"] if g["winner"] == strat1]
    margin2 = [g["margin"] for g in results["detailed_results"] if g["winner"] == strat2]

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
    ax3.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax3.legend()
    margin_hist = fig_to_base64(fig3)
    plt.close(fig3)

    # Margin of victory by game number
    fig4, ax4 = plt.subplots()
    sns.scatterplot(x=game_numbers, y=margins, hue=winners, ax=ax4)
    ax4.set_xlabel("Game Number")
    ax4.set_ylabel("Margin of Victory")
    ax4.set_title("Margin by Game")
    ax4.yaxis.set_major_locator(MaxNLocator(integer=True))
    margin_scatter = fig_to_base64(fig4)
    plt.close(fig4)

    log_items = ""
    for game in results["detailed_results"]:
        log_path = game.get("log_path")
        if log_path:
            rel = os.path.relpath(log_path, output_path.parent)
            log_items += f'<li><a href="{rel}">Game {game["game_number"]}</a></li>'
        else:
            log_items += f'<li>Game {game["game_number"]}: No log available</li>'

    title = f"{strat1} vs {strat2}"

    html = f"""
    <html>
    <head>
        <title>{title} Comparison</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ text-align: center; }}
            img {{ max-width: 800px; display: block; margin: 20px auto; }}
        </style>
    </head>
    <body>
    <h1>{title} Comparison</h1>
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
    <h2>Game Logs</h2>
    <ul>{log_items}</ul>
    </body>
    </html>
    """

    output_path.write_text(html)
    if verbose:
        print(f"Report written to {output_path}")


def generate_sweep_report(
    results: dict,
    output_path: Path,
    *,
    verbose: bool = False,
) -> None:
    """Create an HTML report for a hypothesis sweep or variant comparison.

    Parameters:
        results: Dict from ``HypothesisTester.sweep()`` or ``.compare()``.
            Expected keys: ``baseline_name``, ``games_per_matchup``, ``variants``.
        output_path: Where to write the HTML file.
        verbose: If True, print a confirmation message to stdout.
    """
    sns.set_theme(style="whitegrid")

    baseline_name = results["baseline_name"]
    games = results["games_per_matchup"]
    variants = results["variants"]

    # --- Leaderboard bar chart ---
    names = [v["name"] for v in variants]
    win_rates = [v["win_rate"] for v in variants]

    fig_lb, ax_lb = plt.subplots(figsize=(max(6, len(names) * 1.2), 4))
    colors = ["#2196F3" if v["is_baseline"] else "#4CAF50" if v["win_rate"] >= 50 else "#FF5722" for v in variants]
    sns.barplot(x=names, y=win_rates, palette=colors, ax=ax_lb)
    ax_lb.set_ylabel("Win Rate vs Baseline (%)")
    ax_lb.set_xlabel("Variant")
    ax_lb.set_title("Win Rates Across Variants")
    ax_lb.axhline(y=50, color="gray", linestyle="--", alpha=0.7)
    plt.xticks(rotation=45, ha="right")
    leaderboard_png = fig_to_base64(fig_lb)
    plt.close(fig_lb)

    # --- Summary table rows ---
    table_rows = ""
    for v in variants:
        p_str = f'{v["p_value"]:.4f}' if not v["is_baseline"] else "-"
        avg_str = f'{v["avg_score"]:.1f}' if not v["is_baseline"] else "-"
        style = ' style="background: #e3f2fd;"' if v["is_baseline"] else ""
        table_rows += (
            f"<tr{style}>"
            f'<td>{v["name"]}</td>'
            f'<td>{v["wins"]}</td>'
            f'<td>{v["losses"]}</td>'
            f'<td>{v["win_rate"]:.1f}%</td>'
            f"<td>{avg_str}</td>"
            f"<td>{p_str}</td>"
            f"</tr>\n"
        )

    # --- Per-variant detail charts ---
    detail_sections = ""
    for v in variants:
        if v["is_baseline"]:
            continue

        detailed = v["detailed_results"]
        if not detailed:
            continue

        turns = [g["turns"] for g in detailed]
        margins = [g["margin"] for g in detailed]

        # Game length histogram
        fig_t, ax_t = plt.subplots()
        win_turns = [g["turns"] for g in detailed if g["variant_won"]]
        loss_turns = [g["turns"] for g in detailed if not g["variant_won"]]
        all_turns = win_turns + loss_turns
        if all_turns:
            t_bins = range(min(all_turns), max(all_turns) + 2)
            if win_turns:
                sns.histplot(win_turns, bins=t_bins, alpha=0.6, label="Wins", color="#4CAF50", ax=ax_t)
            if loss_turns:
                sns.histplot(loss_turns, bins=t_bins, alpha=0.6, label="Losses", color="#FF5722", ax=ax_t)
        ax_t.set_xlabel("Turns")
        ax_t.set_ylabel("Games")
        ax_t.set_title(f'{v["name"]} - Game Length')
        ax_t.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax_t.legend()
        turns_png = fig_to_base64(fig_t)
        plt.close(fig_t)

        # Victory margin histogram
        fig_m, ax_m = plt.subplots()
        if margins:
            sns.histplot(margins, bins=30, ax=ax_m, color="#2196F3")
        ax_m.axvline(x=0, color="gray", linestyle="--", alpha=0.7)
        ax_m.set_xlabel("Score Margin (variant - baseline)")
        ax_m.set_ylabel("Games")
        ax_m.set_title(f'{v["name"]} - Victory Margin')
        ax_m.yaxis.set_major_locator(MaxNLocator(integer=True))
        margin_png = fig_to_base64(fig_m)
        plt.close(fig_m)

        detail_sections += f"""
        <div class="variant-detail">
            <h3>{v["name"]}</h3>
            <p>Win rate: {v["win_rate"]:.1f}% | Avg score: {v["avg_score"]:.1f} | p-value: {v["p_value"]:.4f}</p>
            <div class="charts">
                <img src="data:image/png;base64,{turns_png}" />
                <img src="data:image/png;base64,{margin_png}" />
            </div>
        </div>
        """

    html = f"""
    <html>
    <head>
        <title>Hypothesis Sweep: {baseline_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1, h2 {{ text-align: center; }}
            img {{ max-width: 700px; display: block; margin: 15px auto; }}
            table {{ margin: 20px auto; border-collapse: collapse; width: 80%; }}
            th, td {{ border: 1px solid #ccc; padding: 8px 12px; text-align: left; }}
            th {{ background: #f5f5f5; }}
            tr:nth-child(even) {{ background: #fafafa; }}
            .variant-detail {{ border: 1px solid #ddd; margin: 20px auto; padding: 15px; max-width: 900px; border-radius: 4px; }}
            .charts {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; }}
            .charts img {{ max-width: 420px; }}
        </style>
    </head>
    <body>
    <h1>Hypothesis Sweep</h1>
    <p style="text-align:center;">Baseline: <strong>{baseline_name}</strong> | Games per matchup: {games}</p>

    <h2>Win Rate Comparison</h2>
    <img src="data:image/png;base64,{leaderboard_png}" />

    <h2>Summary</h2>
    <table>
        <tr><th>Variant</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>Avg Score</th><th>p-value</th></tr>
        {table_rows}
    </table>

    <h2>Per-Variant Details</h2>
    {detail_sections}
    </body>
    </html>
    """

    output_path.write_text(html)
    if verbose:
        print(f"Report written to {output_path}")


def generate_leaderboard_html(
    results: dict[str, dict[str, any]],
    output_path: Path,
    *,
    verbose: bool = False,
) -> None:
    """Create an HTML leaderboard report for many strategies."""
    sns.set_theme(style="whitegrid")
    sorted_items = sorted(results.items(), key=lambda i: i[1]["win_rate"], reverse=True)
    strategies = [name for name, _ in sorted_items]
    win_rates = [stats["win_rate"] for _, stats in sorted_items]

    fig, ax = plt.subplots(figsize=(8, 4))
    sns.barplot(x=strategies, y=win_rates, ax=ax)
    ax.set_ylabel("Win Rate (%)")
    ax.set_xlabel("Strategy")
    ax.set_title("Strategy Win Rates")
    plt.xticks(rotation=45, ha="right")
    bar_png = fig_to_base64(fig)
    plt.close(fig)

    rows = ""
    for rank, (name, stats) in enumerate(sorted_items, 1):
        cards = stats.get("cards", [])
        cards_str = ", ".join(cards) if cards else "-"
        desc = stats.get("description", "")
        rows += (
            f"<tr><td>{rank}</td><td>{name}</td><td class='desc'>{desc}</td>"
            f"<td>{stats['wins']}</td>"
            f"<td>{stats['losses']}</td><td>{stats['win_rate']:.1f}%</td>"
            f"<td class='cards'>{cards_str}</td></tr>\n"
        )

    html = f"""
    <html>
    <head>
        <title>Strategy Leaderboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ text-align: center; }}
            img {{ max-width: 800px; display: block; margin: 20px auto; }}
            table {{ margin: auto; border-collapse: collapse; width: 90%; }}
            th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
            th {{ background: #f5f5f5; }}
            td.cards {{ font-size: 0.85em; color: #555; max-width: 400px; }}
            td.desc {{ font-size: 0.85em; color: #666; max-width: 300px; }}
            tr:nth-child(even) {{ background: #fafafa; }}
        </style>
    </head>
    <body>
    <h1>Strategy Leaderboard</h1>
    <img src="data:image/png;base64,{bar_png}" />
    <table>
        <tr><th>#</th><th>Strategy</th><th>Description</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>Kingdom Cards Used</th></tr>
        {rows}
    </table>
    </body>
    </html>
    """
    output_path.write_text(html)
    if verbose:
        print(f"Report written to {output_path}")
