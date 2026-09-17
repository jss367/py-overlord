"""Render the three curated search guides from recorded simulation evidence."""

from html import escape
import json
from math import sqrt
from pathlib import Path
from statistics import stdev

from dominion.cards.registry import get_card
from dominion.strategy.strategies.three_unused_kingdoms import (
    KINGDOMS,
    UnusedKingdomPolicy,
)
from scripts.search_three_unused_kingdoms import DATA, ranking


STYLE = """
:root{color-scheme:light;--ink:#203e39;--paper:#f6f3eb;--accent:#8c5027}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:17px/1.65 system-ui,sans-serif}
main{max-width:1080px;margin:auto;padding:32px 25px 70px}a{color:var(--accent)}nav{display:flex;gap:20px;flex-wrap:wrap;font-size:14px}
header{padding:38px 0 22px;border-bottom:1px solid #ccd5c8}h1,h2,h3{font-family:Georgia,serif;line-height:1.18}h1{font-size:clamp(36px,6vw,58px)}h2{font-size:29px;margin-top:40px}
.lead{font-size:21px}.eyebrow{font-size:13px;text-transform:uppercase;letter-spacing:.1em}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}.card{padding:15px;background:#fffdf7;border:1px solid #cdd6c8;border-radius:9px}.card strong,.card small{display:block}.callout{background:#e5eddf;border-left:4px solid #618454;padding:20px 24px;margin:25px 0}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;font-size:15px}td,th{padding:12px;text-align:left;border-bottom:1px solid #cdd6c8;vertical-align:top}th{background:#e5eddf}pre{background:#203e39;color:#fff;padding:20px;overflow:auto;border-radius:8px;font-size:13px}li{margin:9px 0}small,.muted{color:#53675e}details{margin:14px 0}summary{cursor:pointer}footer{margin-top:45px;border-top:1px solid #cdd6c8;padding-top:18px;font-size:14px}
@media(max-width:750px){.cards{grid-template-columns:repeat(2,1fr)}}@media print{nav{display:none}body{background:white}main{padding:0}tr,.card{break-inside:avoid}}
"""

CONTEXT = {
    "sentry_hunting_party": (
        "Sentry and Hunting Party",
        "Sentry can remove starting junk, Hunting Party supplies repeatable draw, and Merchant or Conspirator can turn cycling into money. Bazaar supports terminal Actions; Candlestick Maker supplies an extra buy. The search also tests money decks that skip most of that infrastructure.",
        "Play Bazaar and Candlestick Maker before the draw cards, then Sentry, Merchant, Poacher and Hunting Party. Play Conspirator after those Actions so it can earn its draw and action bonuses. Sentry's current simulator policy automatically trashes Copper, Estate and Curse, discards other plain Victory cards, and keeps useful cards; the search does not vary that policy.",
    ),
    "minion_courtier": (
        "Minion and Courtier",
        "Minion can accumulate action money and replace a weak hand. Courtier can reveal a card with multiple types for several benefits. Diplomat, Baron and Conclave offer alternative support; Trading Post and Replace offer slower deck renovation.",
        "Play multiple Minions for money until only the last remains. Keep a guaranteed $8 hand; otherwise the final Minion redraws when the treasure value left in hand is at or below the policy's threshold. Courtier reveals a card with the most types. If no Actions remain and another Action is in hand, choose an Action before money; otherwise prefer money, Gold, then a buy. Diplomat moves forward when the pre-play hand has at most four cards, allowing its action bonus after drawing. Other choices use the repository's existing card heuristics.",
    ),
    "old_witch_rabble": (
        "Old Witch and Rabble",
        "Old Witch combines draw with Curses, while Rabble attacks the opponent's next draws. Recruiter can turn Estates or Silk Merchants into Villagers, and Spices provides money, a buy and Coffers on gain. Squire and Caravan offer a more conventional engine; Soothsayer offers an alternative curse-and-Gold plan.",
        "Play Squire and Caravan before terminal draw. When attack-first is enabled and Curses remain, move Old Witch ahead of Warehouse and Recruiter. Otherwise follow Warehouse, Recruiter, Old Witch, Rabble, Silk Merchant, Soothsayer and Haggler. Skip Recruiter with no Copper, Estate, Curse or Silk Merchant in hand; when it is played, trash Curse, Estate, Copper, then Silk Merchant in that order. Discard junk first for Warehouse. The simulator spends Villagers as needed to continue playing Actions and uses Coffers to cover purchases.",
    ),
}

RECOMMENDED_PLAY = {
    "sentry_hunting_party": (
        "Play Candlestick Maker, then Sentries, then Hunting Party. After those Actions, play Conspirators for their draw and action bonuses; finish with Vassal. Sentry thins the starting cards while the other Actions provide money and a spare buy. The current simulator's Sentry policy automatically trashes Copper, Estate and Curse and discards other plain Victory cards. The search does not vary those Sentry choices.",
        "The larger Bazaar, Conspirator and Hunting Party engine is a close alternative. The recommended deck uses fewer types of infrastructure and delays Province purchases until turn 12 unless the Province pile is already half empty. The tournament and validation compare complete policies; they do not prove that any individual ownership cap is independently optimal.",
    ),
    "minion_courtier": (
        "Play Baron and discard an Estate when one is available for the $4 bonus. Without an Estate, Baron gains one for future pairings. Keep the starting Estates; buy Gold and Silver after reaching two Barons. Baron also provides a spare buy, so late-game Duchies or Estates can accompany a larger purchase when affordable.",
        "One Baron and one- or two-Courtier money plans are competitive alternatives; the data does not establish a decisive lead over every finalist. The recommendation buys no Minions. This is a result for these tested policies, not a claim that stronger Minion tactics are impossible.",
    ),
    "old_witch_rabble": (
        "Play Caravan before Warehouse, discard Victory cards, Curses and then Copper with Warehouse, and finish with Soothsayer. Soothsayer supplies Gold and curses the opponent; Spices supplies $2 and another buy, plus two Coffers when gained. Use the extra buying power for Provinces from turn eight, or earlier when four or fewer remain. The simulator automatically uses Coffers to cover a purchase when needed.",
        "The recommendation skips Old Witch and Rabble. Soothsayer offers a different attack plan: accumulate Gold while distributing Curses, then use Warehouse to filter weak hands. These are plausible reasons for the complete policy's result, rather than measured single-card effects.",
    ),
}


def label(spec):
    targets = spec.get("targets", [])
    return ", ".join(f"{cap} {name}" for name, cap in targets) or "Treasure-only money"


def interval(row):
    pairs = row["pair_points"]
    error = 1.96 * stdev(pairs) / sqrt(len(pairs))
    return f"{100 * max(0, row['rate'] - error):.1f}–{100 * min(1, row['rate'] + error):.1f}%"


def write_guide(board):
    title, context, _ = CONTEXT[board]
    play, interpretation = RECOMMENDED_PLAY[board]
    slug = board.replace("_", "-")
    screen = json.loads((DATA / f"{board}_screen.json").read_text())
    tournament = json.loads((DATA / f"{board}_tournament.json").read_text())
    validation = json.loads((DATA / f"{board}_validate.json").read_text())
    ordered = ranking(tournament)
    champion = ordered[0][1]
    assert all(r["a"] == champion for r in validation)
    params = UnusedKingdomPolicy(board, **champion).params
    provenance = json.loads(
        Path("scripts/data/three_unused_kingdoms_provenance.json").read_text()
    )
    all_rows = screen + tournament + validation
    total = sum(r["games"] for r in all_rows)
    truncated = sum(r["truncated"] for r in all_rows)
    truncated_note = ""
    if truncated:
        finalist_specs = [p for _, p in ordered]
        affected = any(r["truncated"] and r["a"] in finalist_specs for r in screen)
        truncated_note = (
            f"<p>The {sum(r['truncated'] for r in screen)} truncated screening games were scored at the cutoff. "
            + (
                "At least one finalist's screening results include a truncated game. "
                if affected
                else "None involved a screening candidate that advanced to the finalist tournament. "
            )
            + f"The finalist tournament had {sum(r['truncated'] for r in tournament)} truncations; "
            f"held-out validation had {sum(r['truncated'] for r in validation)}.</p>"
        )
    cards = "".join(
        f'<div class="card"><strong>{escape(n)}</strong><small>${get_card(n).cost.coins}</small></div>'
        for n in KINGDOMS[board]
    )
    targets = "".join(
        f"<li>{escape(name)}: up to <strong>{cap}</strong> owned at a time.</li>"
        for name, cap in params["targets"]
    )
    tournament_rows = "".join(
        f"<tr><td>{i}</td><td>{escape(label(p))}<details><summary>Exact policy</summary><pre>{escape(json.dumps(UnusedKingdomPolicy(board, **p).params, indent=2))}</pre></details></td><td>{rate:.1%}</td></tr>"
        for i, (rate, p) in enumerate(ordered, 1)
    )
    validation_rows = "".join(
        f"<tr><td>{escape(label(r['b']))}<br><small>Opening preference: {escape(r['b'].get('opening', 'Silver'))}</small><details><summary>Exact policy</summary><pre>{escape(json.dumps(UnusedKingdomPolicy(board, **r['b']).params, indent=2))}</pre></details></td><td>{r['wins']} / {r['ties']} / {r['games'] - r['wins'] - r['ties']}</td><td>{r['rate']:.1%}</td><td>{interval(r)}</td><td>{r['scores'][0]:.1f}–{r['scores'][1]:.1f}</td></tr>"
        for r in validation
    )
    money = validation[-2]
    toughest = min(validation[:4], key=lambda r: r["rate"])
    close = [r for r in validation[:4] if float(interval(r).split("–")[0]) <= 50]
    uncertainty = (
        "At least one close finalist is not clearly separated from the recommendation in held-out play. Treat these as competitive alternatives, rather than claiming a uniquely proven winner."
        if close
        else "The recommendation's approximate 95% interval is above 50% against each of the four tested closest finalists."
    )
    if float(interval(toughest).split("–")[1].rstrip("%")) < 50:
        uncertainty = (
            f"Despite the highest overall tournament score, the recommendation scored only {toughest['rate']:.1%} "
            f"against {escape(label(toughest['b']))}; its interval lies below 50%. "
            "That opponent is a demonstrated counter in this matchup. Consider its exact policy above when facing the recommended deck."
        )
    links = " · ".join(
        f'<a href="{key.replace("_", "-")}-strategy-guide.html">{escape(CONTEXT[key][0])}</a>'
        for key in KINGDOMS
        if key != board
    )
    rules_note = ""
    if board == "old_witch_rabble":
        rules_note = '<p><strong>Rules correction before the recorded search:</strong> Soothsayer previously put the opponent\'s Curse directly into their hand. It now gains to the discard pile and then draws a card, following the <a href="https://cs.uwaterloo.ca/~dtompkin/archive/dtlib/expansions/Dominion%20%28Second%20Edition%29%20~%20Guilds.pdf">official Guilds rulebook (archived copy)</a>. Regression tests cover the gain destination and the absence of a draw when Curses run out. All results shown here were regenerated after that correction; the earlier exploratory results were discarded.</p>'
    raw_links = " · ".join(
        f'<a href="../../scripts/data/three_unused_kingdoms/{board}_{stage}.json">{stage.title()} data</a>'
        for stage in ("screen", "tournament", "validate")
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}: Board and Strategy Guide</title><style>{STYLE}</style></head><body><main>
<nav><a href="index.html">Strategy catalog</a><a href="../boards/{slug}.html">Board details</a><a href="{slug}-best-found.html">Runnable strategy</a></nav>
<header><p class="eyebrow">Three kingdoms from previously unused cards · September 17, 2026</p>
<h1>{title}</h1><p class="lead">Ten previously unused kingdom piles, a reproducible strategy search, and a practical plan for the strongest policy found.</p></header>
<h2>The kingdom</h2><div class="cards">{cards}</div>
<p>Two players. Standard supply and starting decks: seven Coppers and three Estates each. No landscapes, Shelters, Colony, Platinum or Potion. The three kingdoms share no kingdom cards.</p><p>{context}</p>
<h2>The overall tournament winner</h2><div class="callout"><strong>{escape(label(champion))}.</strong> This policy scored {ordered[0][0]:.1%} in the eight-policy finalist tournament and {money["rate"]:.1%} against treasure-only money on 1,000 fresh validation games. Ties count as half a win.</div>
<p><strong>Matchup caveat:</strong> its toughest tested finalist matchup was {escape(label(toughest['b']))}, against which it scored {toughest['rate']:.1%} (approximate 95% interval {interval(toughest)}). The recommendation optimizes the overall tournament result; opponent-specific counters and close alternatives matter.</p>
<p><strong>Opening preference:</strong> {escape(params["opening"])}. During your first two turns, prefer that card when affordable and not already owned; otherwise follow the purchase priorities below. This specifies a preference, not a guaranteed opening split.</p>
<ol><li>Buy Province from your turn {max(1, params["green"])}, or whenever four or fewer Provinces remain.</li>
<li>Buy Duchy at {params["duchy"]} or fewer Provinces remaining, and Estate at one or fewer. These scoring buys precede deck-building targets.</li>
<li>Next take the first affordable card below whose ownership target has not been met, in the listed order. Cards lower on the list can be bought before a more expensive target when money is short.<ol>{targets}</ol></li>
<li>Then buy Gold up to {params["gold"]} copies and Silver up to {params["silver"]}. A cap of 99 is effectively uncapped. Pass if nothing on the list is affordable; do not add early Estates or extra Copper.</li></ol>
<p>{play}</p><p>{interpretation}</p>
<details><summary>Exact recommended parameters</summary><pre>{escape(json.dumps(params, indent=2))}</pre></details>
<h2>What the search establishes</h2><p>{len(ranking(screen, screening=True))} candidate policies were screened against four fixed opponents, with 40 games per pairing. Candidates included one-, two- and five-copy plans for every pile, money baselines, seeded engines and randomized mixtures. The top eight advanced to a complete round robin: 240 games per pairing, 1,680 per entrant. The tournament winner was frozen, then faced four finalists and two baselines for 1,000 games each on disjoint fresh seeds.</p>
<p>Every random seed is played in both seats. Scores include the equal-score, fewer-turns tiebreaker. In total, this board contributed <strong>{total:,} games</strong>: {sum(r["games"] for r in screen):,} screening, {sum(r["games"] for r in tournament):,} tournament and {sum(r["games"] for r in validation):,} validation. <strong>{truncated} games reached the safeguard without a normal ending.</strong> All displayed rates include ties as half a win.</p>
{truncated_note}
<div class="scroll"><table><caption>Finalist tournament</caption><thead><tr><th>Place</th><th>Policy</th><th>Score rate</th></tr></thead><tbody>{tournament_rows}</tbody></table></div>
<h3>Held-out validation</h3><div class="scroll"><table><caption>The frozen tournament winner versus each opponent; 1,000 games per row</caption><thead><tr><th>Opponent</th><th>Wins / ties / losses</th><th>Score rate</th><th>Approx. 95% interval</th><th>Mean points, winner–opponent</th></tr></thead><tbody>{validation_rows}</tbody></table></div>
<p>Intervals use the standard error of the 500 two-seat pair scores, preserving dependence within each seeded pair. They describe simulation uncertainty for a fixed matchup and are not adjusted for multiple comparisons. {uncertainty}</p>
<p><strong>Scope:</strong> this is the best policy found within the tested purchase plans and decision rules, not a proof of optimal Dominion play. The search varies ownership caps, purchase order, opening preference, treasure density, greening, and two play settings. It does not exhaust tactical policies, tune every card-specific choice, or model human opponents. Results use this repository's simulator, including its fixed card heuristics; they are not an independent certification of all card rules. Finalists differ in multiple settings, so their ranking does not isolate the value of a single card.</p>
{rules_note}
<h2>Why these cards qualify</h2><p>Before writing these strategies, all 30 selected kingdom cards had zero references in the catalog of {provenance["strategy_count"]} registered strategies. An additional syntax-tree scan found no exact card-name string literals in the existing Python strategy modules, including unpublished variants. Basic supply and starting cards are exempt. This is a repository-specific definition: it does not claim these cards are unused in Dominion generally, and indirect or dynamically constructed references can escape a static audit.</p>
<p>The baseline revision is <code>{provenance["revision"]}</code>. The <a href="../../scripts/data/three_unused_kingdoms_provenance.json">selection audit</a> preserves the original candidate pool and all three boards. Newly published strategies will now make their chosen cards appear as used.</p>
<h2>Reproduce the results</h2><pre>PYTHONPATH=. python scripts/search_three_unused_kingdoms.py screen --board {board}
PYTHONPATH=. python scripts/search_three_unused_kingdoms.py tournament --board {board}
PYTHONPATH=. python scripts/search_three_unused_kingdoms.py validate --board {board}
PYTHONPATH=. python scripts/write_three_unused_kingdom_guides.py
PYTHONPATH=. python scripts/render_catalog.py
git restore -- reports/strategies/leaderboard.html</pre>
<p>{raw_links}. Parameters, seeds, wins, ties, game lengths, truncations and mean final decks are recorded. The search source is <a href="../../scripts/search_three_unused_kingdoms.py">available here</a>; runnable policies live in <a href="../../dominion/strategy/strategies/three_unused_kingdoms.py">the strategy module</a>.</p>
<footer>Explore the other two kingdoms: {links}.</footer></main></body></html>
"""
    path = (
        Path("dominion/reporting/curated_strategy_guides")
        / f"{slug}-strategy-guide.html"
    )
    path.write_text(html)
    print(path)


if __name__ == "__main__":
    for board in KINGDOMS:
        write_guide(board)
