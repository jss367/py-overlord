"""Regenerate the Kimberley guide from the recorded search results.

Run from the repository root with PYTHONPATH=. after ``search_kimberley.py final``:

    PYTHONPATH=. python scripts/write_kimberley_guide.py --rev <sha> --tests "<summary>"
"""

import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--rev", required=True, help="Short git revision the validation ran at")
parser.add_argument("--search-rev", default="ff0d398", help="Short git revision the recorded search results were produced at")
parser.add_argument("--tests", required=True, help="HTML fragment describing the validation run")
parser.add_argument("--date", default="September 9, 2026")
args = parser.parse_args()
from scripts.search_kimberley import ablations, best_no_mine, FINAL
final = json.load(open("docs/analysis/kimberley_final.json"))
nm = best_no_mine()
changes = dict(ablations(FINAL), throne_room=dict(FINAL, thrones=1), kings_court=dict(FINAL, kings=1), two_mines=dict(FINAL, mines=2), lab_opening=dict(FINAL, opening="Laboratory"), silver_second=dict(FINAL, second="Silver"))
key = lambda s: json.dumps(s, sort_keys=True)
inv = {key(v): k for k, v in changes.items()}
pct = lambda x: f"{100*x:.1f}%"
res = {}
for x in final:
    res[(key(x["a"]), key(x["b"]))] = x
def rate(a, b): return res[(key(a), key(b))]["rate"]
money_labels = {"plain": "Colony Big Money (Platinum, Gold, Silver only)", "Smithy": "Colony Big Money with up to two Smithies", "Laboratory": "Colony Big Money with up to three Laboratories", "Mine": "Colony Big Money with up to two Mines (climbing to Platinum)", "Priest": "Colony Big Money with one Priest", "Hoard": "Colony Big Money with up to two Hoards", "Bank": "Colony Big Money with up to two Banks"}
rows = [f"<tr><td>Best no-Mine plan from the search (Priest opening, three Laboratories, King's Court with Smithy, three Market Squares, Hoard, Bank)</td><td style=\"text-align: right;\">{pct(rate(FINAL, nm))}</td></tr>"]
for mode, lab in money_labels.items():
    rows.append(f"<tr><td>{lab}</td><td style=\"text-align: right;\">{pct(rate(FINAL, {'money': mode}))}</td></tr>")
change_labels = {
    "no_mine": "Never buy Mine (Laboratory opening instead)",
    "no_sewers": "Never buy Sewers",
    "no_priest": "Never buy Priest (Silver second)",
    "no_squares": "Never buy Market Square",
    "copper_first": "Mine upgrades Copper first instead of taking the biggest step",
    "throne_room": "Add one Throne Room, pointed at Mine",
    "kings_court": "Add one King's Court, pointed at Mine",
    "two_mines": "Buy a second Mine",
    "lab_opening": "Open Laboratory instead of Mine",
    "silver_second": "Open Silver instead of Priest as the second card",
}
arows = []
for k, lab in change_labels.items():
    spec = changes[k]
    arows.append(f"<tr><td>{lab}</td><td style=\"text-align: right;\">{pct(rate(FINAL, spec))}</td><td style=\"text-align: right;\">{pct(rate(spec, nm))}</td></tr>")
first = json.load(open("docs/analysis/kimberley_confirm.json"))
screen = json.load(open("docs/analysis/kimberley_screen.json")); recheck = json.load(open("docs/analysis/kimberley_recheck.json")); nomine = json.load(open("docs/analysis/kimberley_nomine.json"))
total = sum(x["games"] for x in screen + recheck + nomine + first + final)
nm_vs_smithy = next(x for x in first if x["a"] == nm and "money" in x["b"])["rate"]
tomb = sum(x["totals"]["tomb_points"] for x in final if x["a"] == FINAL) / sum(x["games"] for x in final if x["a"] == FINAL)
style = re.search(r"<style>.*?</style>", Path("dominion/reporting/curated_strategy_guides/mine-guildhall-strategy-guide.html").read_text(), re.S).group(0)
vs_nm, vs_sm = pct(rate(FINAL, nm)), pct(rate(FINAL, {"money": "Smithy"}))
def ci(a, b):
    lo, hi = res[(key(a), key(b))]["paired_ci95"]
    return lo, hi
short_labels = {
    "no_mine": "no Mine", "no_sewers": "no Sewers", "no_priest": "no Priest",
    "no_squares": "no Market Square", "copper_first": "Copper-first upgrades",
    "throne_room": "adding Throne Room", "kings_court": "adding King's Court",
    "two_mines": "a second Mine", "lab_opening": "the Laboratory opening",
    "silver_second": "Silver as the second card",
}
unseparated = ", ".join(
    short_labels[k]
    for k in change_labels
    if ci(FINAL, changes[k])[0] <= 0.5 <= ci(FINAL, changes[k])[1]
)
two_mine_ci = "%s to %s" % tuple(pct(v) for v in ci(FINAL, changes["two_mines"]))
html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Kimberley: a Colony board where Mine climbs Copper to Platinum in hand and Sewers, Tomb, Priest, and Market Square pay out on every trash.">
<title>Kimberley Mine Engine Guide</title>
{style}
</head>
<body>
<main class="page">
<nav class="topbar" aria-label="Guide navigation"><a href="index.html">← Strategy catalog</a><a href="../boards/kimberley.html">View the board</a><a href="kimberley-mine-engine.html">Strategy implementation</a></nav>
<header class="hero">
<div class="intro"><span class="eyebrow">Board built for Mine</span><h1>Kimberley</h1><p><strong>A two-player Colony board where Mine is the best card.</strong> Mine trashes a Treasure and gains one costing up to $3 more directly into hand, so one play turns Gold into Platinum you spend the same turn. Kimberley surrounds it with cards that pay out on every trash: Sewers trashes a second card, Tomb awards a point, Priest adds $2, and Market Square turns into a Gold.</p>
<p>The published engine won {vs_nm} of confirmation games against the strongest plan the search found that never buys Mine, and {vs_sm} against Colony Big Money with Smithy.</p>
</div>
<aside class="verdict" aria-label="Recommendation"><span class="eyebrow">Mine engine vs best no-Mine plan</span><strong>{vs_nm}</strong><p>1,000 paired games per opponent. Buy one Mine with your first $5 (turn one or two on a $5/$2 split, otherwise the first later $5), play it every turn it can climb, and skip both multipliers.</p><p>Two players · Estate starts · Colony and Platinum · Sewers · Tomb</p></aside>
</header>
<nav class="contents" aria-label="On this page"><a href="#the-board">The board</a><a href="#how-to-play-it">How to play it</a><a href="#what-the-simulations-established">What the simulations established</a><a href="#reproduction">Reproduction</a></nav>
<section class="section"><h2 id="the-board">The board</h2>
<p>Kingdom: Mine, Throne Room, King's Court, Laboratory, Smithy, Mining Village, Market Square, Priest, Hoard, Bank. Colony and Platinum are in the supply. Landscapes: the Sewers project and the Tomb landmark. Board file: <a href="../../boards/kimberley.txt"><code>boards/kimberley.txt</code></a>. The multipliers are on the board because Mine is the card they most want to repeat; the search found the engine is stronger without them, and the ablation table below shows by how much.</p>
<div class="table-wrap" role="region" aria-label="Why each piece is here" tabindex="0"><table>
<thead><tr><th>Piece</th><th>What it does for Mine</th></tr></thead>
<tbody>
<tr><td>Platinum and Colony</td><td>Gives Mine a top rung. Gold costs $6, so Mine reaches Platinum ($9) in one step, and Colonies keep the game long enough for the climb to matter.</td></tr>
<tr><td>Sewers</td><td>Every Mine play trashes a second card from hand. The engine removes Estates and spare Coppers without a dedicated trasher.</td></tr>
<tr><td>Tomb</td><td>+1 VP per trash. With Sewers doubling trashes, the published engine banks about {tomb:.0f} Tomb points per game.</td></tr>
<tr><td>Priest</td><td>+$2 per later trash this turn. Played before Mine, it turns each climb into money as well.</td></tr>
<tr><td>Market Square</td><td>Reacts to any trash by becoming a Gold, which Mine later turns into Platinum. Its +Buy spends the surplus.</td></tr>
<tr><td>Throne Room, King's Court</td><td>Repeat Mine: Copper to Silver to Gold, or Gold to Platinum twice. Tempting, but neither helped in testing: King's Court at $7 competes with Platinum, and Throne Room at $4 competes with Priest and Sewers while needing Mine in the same hand.</td></tr>
<tr><td>Laboratory, Smithy, Mining Village</td><td>Draw and Actions so Mine and Priest can both fire. Mining Village trashing itself also triggers Sewers and Tomb.</td></tr>
<tr><td>Hoard, Bank</td><td>Alternative Mine targets from Silver and Gold. Neither beat plain Platinum climbing in the search.</td></tr>
</tbody></table></div>
</section>
<section class="section"><h2 id="how-to-play-it">How to play it</h2>
<ol>
<li><strong>Open Mine/Priest.</strong> On $5/$2 buy Mine and nothing; on $4/$3 buy Priest and Silver or Market Square. Opening Laboratory instead of Mine was within noise; opening Silver instead of Priest lost clearly.</li>
<li><strong>One Mine is enough.</strong> A second Mine lost {pct(rate(FINAL, changes["two_mines"]))} of games to the single-Mine engine. Play Mine every turn it can climb: trash Gold when Platinum remains in the supply, otherwise Silver, otherwise Copper. Never trash Platinum. Upgrading Copper first instead lost {pct(rate(FINAL, changes["copper_first"]))}.</li>
<li><strong>Buy Sewers on your first $3 hand.</strong> Sewers costs $3 and Mining Village $4, so a $3 hand buys Sewers; with $4 the engine takes its first Mining Village once it owns two terminals and Sewers right after. Sewers converts every Mine play into two trashes. Let it eat Estates first, then Coppers while you own more than three. Skipping Sewers, skipping Priest, and opening Silver instead of Priest were the three costliest changes tested after skipping Mine.</li>
<li><strong>Priest before Mine when you have the Actions.</strong> Mining Village supplies the second Action; Laboratory only replaces the one it costs, so a Laboratory, Priest, and Mine hand strands one terminal. Priest trashes an Estate or Copper, then Mine's trash and the Sewers trash each add $2. Skipping Priest lost {pct(rate(FINAL, changes["no_priest"]))} of games to the published engine. Market Square was close to neutral on its own; it is there for the Gold reaction and the +Buy.</li>
<li><strong>Skip Throne Room and King's Court.</strong> The engine plays one Mine per turn and wants every other purchase to be Platinum, draw, or a trash trigger. Adding one Throne Room lost {pct(rate(FINAL, changes["throne_room"]))} to the published engine; adding one King's Court was a coin flip. If you do own one, point it at Mine.</li>
<li><strong>Money: Platinum at $9, one Gold, one Silver.</strong> Mine manufactures the rest. The buy order after points and Platinum is Gold, Mine, Laboratory, the first Mining Village (once two terminals are owned), Priest, Sewers, Market Square, then Silver, each up to its cap.</li>
<li><strong>Green late.</strong> Buy Colony once you own a Platinum, Province once four or fewer Colonies remain, Duchy at two. Tomb points arrive on their own; the engine scores about {tomb:.0f} of them a game.</li>
</ol>
<p>Key rules: Mine gains the new Treasure to your hand, so it is playable this turn. Sewers triggers on each trash, including Priest's own trash and Mining Village trashing itself. Priest's +$2 applies only to trashes after its own. See the <a href="https://wiki.dominionstrategy.com/index.php/Mine">Mine</a>, <a href="https://wiki.dominionstrategy.com/index.php/Sewers">Sewers</a>, and <a href="https://wiki.dominionstrategy.com/index.php/Priest">Priest</a> rules.</p>
</section>
<section class="section"><h2 id="what-the-simulations-established">What the simulations established</h2>
<p>The search played {total:,} games: a 340-candidate screen at 32 games each against Colony Big Money with Smithy, a 40-candidate recheck at 400 games, a separate 120-candidate search for the best plan that never buys Mine (with an eight-candidate recheck), a first confirmation of the recheck leader, and a final confirmation of the published engine after the first confirmation's ablations showed it was stronger without Throne Room. Seats alternate; each shuffle seed is used in both seats; equal scores use the fewer-turns tiebreak and complete ties count as half a win. No game reached the turn limit.</p>
<p>The best no-Mine plan the search found (Priest opening, three Laboratories, King's Court with Smithy, three Market Squares, Hoard and Bank) won {pct(nm_vs_smithy)} against Colony Big Money with Smithy. Final confirmation of the published engine, 1,000 games per opponent:</p>
<div class="table-wrap" role="region" aria-label="Confirmation results" tabindex="0"><table>
<thead><tr><th>Opponent</th><th style="text-align: right;">Published engine's win rate</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<p>Changing one thing about the published engine, 1,000 games each. The first column is the published engine against the changed version; the second is the changed version against the best no-Mine plan.</p>
<div class="table-wrap" role="region" aria-label="Ablation results" tabindex="0"><table>
<thead><tr><th>Change</th><th style="text-align: right;">Published engine vs change</th><th style="text-align: right;">Changed engine vs best no-Mine plan</th></tr></thead>
<tbody>
{chr(10).join(arows)}
</tbody></table></div>
<p>Approximate sampling uncertainty for a 1,000-game result near 50% is three percentage points, before allowing for dependence between paired games. Changes whose paired 95% interval includes 50% ({unseparated}) are not separated from the published engine; the second Mine's interval ({two_mine_ci}) sits just above it.</p>
<p><strong>Practical takeaway:</strong> Mine is the engine here, not a support card. The same policy family without Mine falls from {vs_nm} to {pct(rate(changes["no_mine"], nm))} against the best no-Mine plan, and Sewers and Priest are the pieces that make the difference: Sewers turns each Mine play into a second trash and a second Tomb point, and Priest turns both trashes into money. The multipliers that seem made for Mine are the trap.</p>
</section>
<section class="section"><h2 id="reproduction">Reproduction</h2>
<p>The registered <a href="../../generated_strategies/kimberley_mine_engine.py">strategy implementation</a> is named <strong>Kimberley Mine Engine</strong>. Its decision hooks choose the Mine trash and gain, the multiplier target when one is owned, and the buy order; the static gain list records referenced cards and is not a literal purchase order. Class parameters preserve the alternatives used in the search.</p>
<pre><code class="language-bash">PYTHONPATH=. python scripts/search_kimberley.py screen
PYTHONPATH=. python scripts/search_kimberley.py recheck
PYTHONPATH=. python scripts/search_kimberley.py nomine
PYTHONPATH=. python scripts/search_kimberley.py confirm
PYTHONPATH=. python scripts/search_kimberley.py final
</code></pre>
<p>The script uses six worker processes. Raw results are in <a href="../../docs/analysis/kimberley_screen.json">the screen</a>, <a href="../../docs/analysis/kimberley_recheck.json">the recheck</a>, <a href="../../docs/analysis/kimberley_nomine.json">the no-Mine search</a>, <a href="../../docs/analysis/kimberley_confirm.json">the first confirmation</a>, and <a href="../../docs/analysis/kimberley_final.json">the final confirmation</a>.</p>
<p>Corrections made before these results were recorded:</p>
<ul>
<li>Sewers reads "when you trash a card <strong>other than with this</strong>, you may trash a card from your hand." The simulator let the Sewers trash re-trigger Sewers, so one trash could chain through every Estate and Copper in hand. It now yields at most one extra trash per trash, while Tomb, Priest, and Market Square still see both. Regression tests are in <code>tests/test_sewers_project.py</code>. The whole search was rerun after this fix; the earlier run had overstated the Sewers ablation. See the <a href="https://wiki.dominionstrategy.com/index.php/Sewers">Sewers rules</a>.</li>
<li>The Colony Big Money baselines with Hoard and Bank originally ranked Gold above their support card, so they never bought it. They now buy Hoard or Bank ahead of Gold until the cap.</li>
</ul>
<p>The implementations of Mine, Throne Room, King's Court, Priest, Mining Village, Market Square, Hoard, Bank, and Tomb were also read against the card rules. Mine gains to hand and limits the gain to $3 above the trashed Treasure's cost; Tomb, Priest, Sewers, and Market Square all resolve from the shared trash hook.</p>
<p>The screen, recheck, no-Mine search, and first confirmation were recorded at revision <code>{args.search_rev}</code>, the first commit containing the Sewers correction and its tests. The final confirmation, which is the evidence presented above, was rerun at revision <code>{args.rev}</code> after a second correction: the strategy now plays Priest before a multiplier aimed at Mine when it has the Actions, so repeated Mine trashes collect Priest's bonus. The earlier stages ran with the older ordering; they only chose the configuration to confirm, and the multiplier comparisons above use the corrected play. Validation on {args.date}, at revision <code>{args.rev}</code>: {args.tests}. The commit that regenerates this guide follows that revision and changes only this file and its published copy.</p>
<p>The search compares implemented buying and tactical policies for two players. It does not exhaust every opening or Bank and Hoard line, and the no-Mine reference is the best of 120 random configurations of the same policy family, not a proof that no better Mine-free plan exists.</p></section>
<footer>Repository simulations and official card rules. Best policies found within the tested search; not a proof of optimal play. <a href="index.html">Return to the strategy catalog</a>.</footer>
</main>
</body>
</html>
'''
Path("dominion/reporting/curated_strategy_guides/kimberley-mine-engine-strategy-guide.html").write_text(html)
print(f"written: {total:,} games, {tomb:.1f} Tomb points per game")
