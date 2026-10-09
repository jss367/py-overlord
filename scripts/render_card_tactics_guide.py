"""Publish the recorded card-decision panel as a curated HTML guide."""

from html import escape
import json
from pathlib import Path

from scripts.evaluate_card_tactics import sha256

SOURCE = Path("dominion/reporting/curated_strategy_guides/card-reactions-investment-and-exile-evaluation.html")


def percent(value):
    return f"{100 * value:+.1f}"


def bounds(values, scale=1):
    return f"[{values[0] * scale:+.2f}, {values[1] * scale:+.2f}]"


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + ''.join(f'<th>{escape(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(f'<td>{escape(str(c))}</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def render():
    screen_path = Path("scripts/data/card_tactics_screen.json")
    validation_path = Path("scripts/data/card_tactics_validation.json")
    screen, validation = [json.loads(p.read_text()) for p in (screen_path, validation_path)]
    if validation["selection_sha256"] != sha256(screen_path):
        raise ValueError("Validation does not reference this selection evidence")
    if screen["recommendations"] != validation["recommendations"]:
        raise ValueError("Validation changed the locked recommendations")
    body = ['''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Watchtower, Clerk, Investment and Bounty Hunter: Tactical Evaluation</title>
<style>body{font:16px/1.6 system-ui,sans-serif;color:#202b38;background:#f6f8fa;margin:0}main{max-width:1180px;margin:auto;padding:40px 28px}h1{line-height:1.15;font-size:2.3rem}h2{margin-top:2.2em}a{color:#1763a6}code{font-size:.88em;overflow-wrap:anywhere}pre{padding:18px;background:#e8eef4;overflow:auto;line-height:1.4}.table-scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:.86rem;background:white}th,td{padding:10px 12px;border-bottom:1px solid #d8e0e8;text-align:left;vertical-align:top}th{background:#e5edf5}tr:nth-child(even){background:#f4f7fa}.recommendation{padding:18px 24px;border-left:5px solid #277b64;background:#e7f3ed}.muted{color:#506174}details{margin:18px 0}summary{cursor:pointer;font-weight:600}@media print{main{padding:0}.table-scroll{overflow:visible}body{background:white}table{font-size:9pt}}</style></head><body><main>
<p><a href="index.html">Strategy catalog</a> · <a href="../../docs/card-tactical-inventory.md">Complete card evidence inventory</a></p>
<h1>Watchtower, Clerk, Investment and Bounty Hunter: Tactical Evaluation</h1>
<p class="muted">October 8, 2026 · Four connected decisions · One declared kingdom · 7,200 games</p>
<div class="recommendation"><strong>Keep the current shared defaults for this panel.</strong> The screen selected that recommendation before fresh validation. The contextual Investment alternative loses substantially; Watchtower, Clerk and Bounty Hunter win-share differences remain uncertain. The scenario exceptions below justify further policy work, not a blanket replacement.</div>
<p>Regression tests establish that a decision executes. This study separately measures tactical quality. No production baseline or registered strategy is changed. “Evaluated” here means a bounded comparison on this board, including regressions. Clerk's attack response is compared; its always-play start-of-turn reaction is held constant and remains tactically unevaluated.</p>
<h2>What the policies can decide</h2>
''']
    body.append(table(("Card / decision", "Current normal-strategy default", "Frozen diagnostic alternative", "Scope"), [
        ("Watchtower gain reaction", "Trash Curse/Copper/Ruins; keep pure Victory cards; topdeck Action/Treasure gains costing at least $4.", "Keep Copper when total printed Treasure income is at most $4; keep a terminal Action gain in discard when at least three terminal Actions are owned; otherwise inherit the default.", "Ordinary registered card types and printed income; special effects and complete action sequencing unreviewed."),
        ("Clerk victim topdeck", "Rank junk names (including Copper) ahead of most other cards.", "Put a pure Victory card on deck before giving up economy; otherwise inherit the default.", "Only the attack opponent fires this response in matches. Both arms always play Clerk's start-turn reaction."),
        ("Investment mode", "After mandatory hand trash, estimate remaining Treasure variety excluding a helper-selected Treasure; cash out if at least two names remain.", "Keep Investment for +$1 until Province has at most two cards; then self-trash if any live Treasure name remains.", "The engine trashes Investment itself in cash-out mode and counts every remaining Treasure name. Mandatory trash priorities and Treasure play order are identical across arms."),
        ("Bounty Hunter exile", "Prefer scoring/junk cards even when the name is already exiled; otherwise favor a fresh name and cheaper cards.", "At Province ≤2, switch from a repeated-name target to a fresh name only when the +$3 lifts printed current-hand income from below $8 to at least $8.", "Exiled cards remain owned/scoring. Breakpoint uses current coins and printed hand Treasure income; future Action effects are not modeled."),
    ]))
    body.append('''<p>The ordinary base AI and normal strategy defaults can differ: for example base AI Watchtower only trashes Curse. These matches use <code>GeneticAI(EnhancedStrategy)</code> or its diagnostic subclass. For each card, the other three overrides are rebound to the production implementation, isolating the named decision. Counter instrumentation records engine-to-AI choices in every game.</p>
<h2>Board, purchases and opponents</h2>''')
    body.append('<p>Kingdom: ' + escape(', '.join(validation['kingdom'])) + '. Standard starting decks and base piles; no Colony/Platinum or landscapes.</p>')
    body.append('''<p>Each subject buys Province, Gold, up to two copies of its named card, one Smithy, Duchy at three or fewer Provinces, Silver, then Estate at one or fewer Provinces. Its named Action plays before Smithy. Treasures play Investment before Gold, Silver and Copper. Hand trash prefers Curse, Estate above two Provinces, then Copper when total printed Treasure income exceeds $4. Purchases, hand play order and rules are fixed across both arms.</p>
<p>The money and engine opponents are the registered <code>create_big_money_smithy</code> and <code>create_village_smithy_lab</code> factories, run on the declared board. This board has no Chapel, so the engine's Chapel preference cannot fire; its validation win shares show a weak opponent here. The third opponent buys Province, one Witch, two Clerks, Gold, late Duchy and Silver, and plays Witch before Clerk. Every opponent uses current defaults. Conclusions are conditional on these opponents and this board, not a ranking of all four cards.</p>
<h2>Selection before fresh validation</h2>
<p>The screen used 50 independent seed blocks per comparison, both seats and both policies: 2,400 games. Its predetermined rule selected a contextual policy only if the lower win-share delta bound was positive against all three opponents. All four recommendations were <strong>default</strong>. Validation loaded and hashed that complete screen artifact before any games; it could not change recommendations. Validation used 100 new seed blocks per comparison: 4,800 games. Testing both frozen alternatives on fresh seeds exposes regressions without selecting a new recommendation on the validation outcomes.</p>
''')
    for study in (screen, validation):
        body.append(f'<h3>{"Screen" if study["phase"] == "screen" else "Fresh validation"}</h3>')
        rows = []
        for row in study['comparisons']:
            p = row['policies']
            rows.append((row['card'], row['opponent'], f"{row['seed_start']}–{row['seed_start'] + row['seed_pairs'] - 1}",
                f"{p['default']['win_share']:.1%}", f"{p['contextual']['win_share']:.1%}",
                percent(row['win_share_delta']), bounds(row['delta_95_interval'], 100)))
        body.append(table(("Card", "Opponent", "Seeds (both seats)", "Default win share", "Alternative win share", "Change (percentage points)", "95% change bound (points)"), rows))
    body.append('''<p>Wins count 1, ties ½ and losses 0. Scores and fewer turns taken determine rank, matching the simulator's tie-break rule. Uncertainty uses independent seed blocks, averaging the correlated seats before comparison: 95% Hoeffding bounds for [0,1] win shares and [−1,1] paired changes. Bounds remain nonzero for identical observed results. At 100 seeds the change bound has a conservative ±27.16 percentage-point radius. These are per-comparison bounds, without multiple-comparison adjustment. Equal initial seeds do not force identical subsequent draws when policies consume different random sequences. Full rate bounds, physical scores, turns, per-game hook counters and paired raw outcomes are saved in the JSON artifacts.</p>
<h2>Regressions and score margins</h2>''')
    body.append(table(("Card", "Opponent", "Default score margin", "Alternative score margin", "Change", "Approximate 95% paired score-change interval"), [
        (r['card'], r['opponent'], f"{r['policies']['default']['score_margin']:+.2f}",
         f"{r['policies']['contextual']['score_margin']:+.2f}", f"{r['score_margin_delta']:+.2f}",
         bounds(r['score_delta_approximate_95_interval'])) for r in validation['comparisons']]))
    truncated = sum(p['truncated_games'] for s in (screen, validation) for r in s['comparisons'] for p in r['policies'].values())
    body.append(f'''<p>The Investment alternative regresses against every opponent: −44.5, −21.0 and −21.5 percentage points in fresh validation. Its money-opponent win-share bound excludes zero; all three approximate score-change intervals are negative. Keeping Investment longer also prolongs mandatory hand trashing, so a locally attractive final cash-out can still weaken the whole policy. The other alternatives show small or mixed win-share changes. Some positive score intervals are exploratory and do not establish better win rates. {truncated} games reached the runner's {validation['turn_limit']}-turn safety cap or ended without normal pile exhaustion.</p>
<h2>Reproducible decision scenarios</h2>
<p>The same four stages run through physical card effects or the gain-reaction path for both policies. Watchtower stays in hand while gaining a card; Clerk attacks a legal five-card hand; Investment is physically in play and first performs its mandatory hand trash; Bounty Hunter's Exile pile is explicit. “Excessive copies” stresses crowded Actions, or multiple Investments. These are observed decisions rather than assertions of optimal play.</p>
<details><summary>Show all 32 scenario outcomes and starting conditions</summary>''')
    body.append(table(("Card", "Stage / policy", "Initial hand", "Initial Exile / Provinces", "Chosen response", "Result"), [
        (r['card'], f"{r['stage']} / {r['policy']}", ', '.join(r['initial']['hand']),
         f"{', '.join(r['initial']['exile']) or 'empty'} / {r['initial']['provinces']}",
         '; '.join(r['decisions']),
         f"trash: {', '.join(r['trash']) or 'none'}; deck: {', '.join(r['deck']) or 'empty'}; exile: {', '.join(r['exile']) or 'empty'}; coins: {r['coins']}; point tokens: {r['vp_tokens']}" +
         (f"; gain: {r['initial']['gain']}; discard: {', '.join(r['discard']) or 'empty'}" if r['card'] == 'Watchtower' else ''))
        for r in validation['scenarios']]))
    body.append('''</details><p>The Watchtower early-economy and crowded-Action scenarios differ even though game-level gains remain uncertain. Clerk puts Copper onto the deck while holding a Province in the crowded-hand scenario; the alternative preserves Copper. Investment's endgame scenario leaves Silver and Gold after trashing Copper: cashing out awards two points, while the default takes +$1. With multiple Investments still in hand, their common name counts only once. Bounty Hunter's repeated-Estate endgame scenario yields no bonus under the default; switching to fresh Copper yields +$3 and exposes the economy tradeoff.</p>
<h2>Rules, wiring and search limitations</h2>
<p><a href="../../docs/card-tactical-inventory.md">The evidence inventory</a> covers all 610 registered names by expansion and lists 42 scoped reviewed entries, including ten Knight members whose other effects remain unreviewed. It marks the other 568 entries explicitly unreviewed. Card rules tests, actual engine hooks and tactical quality occupy separate columns. Barge/Sleigh forwarding and Torturer response evaluation remain with <a href="https://github.com/jss367/py-overlord/issues/393">the timing and reaction work</a>. Existing supply-proxy, scheduling and Pillage rules defects retain their individual issues.</p>
<p>Follow-ups: <a href="https://github.com/jss367/py-overlord/issues/411">Investment remaining-hand accounting and cash-out policy</a>, <a href="https://github.com/jss367/py-overlord/issues/412">Ironworks and Engineer free-gain context</a>, and <a href="https://github.com/jss367/py-overlord/issues/413">Searchable contextual decision parameters</a>. Bounty Hunter already has evolvable exile priorities; those genes do not expose this full contextual bonus policy. Python reaction/timing overrides are not automatically optimizer parameters. No evolutionary search was performed here.</p>
<p>Registered strategies need reevaluation on their own boards when a production baseline changes. This study makes no such change and does not refresh or overwrite global standings. The earlier <a href="supply-action-selection-evaluation.html">supply selection</a>, <a href="free-gains-and-quartermaster-policy-evaluation.html">free-gain/storage</a> and <a href="trashing-discard-and-next-turn-card-decisions.html">set-aside/discard</a> evaluations retain their affected-strategy reevaluations and limitations. Opponent factories here supply references, not a new tournament ranking.</p>
<h2>Reproduction and evidence</h2>
<p>Choose fresh output paths: the evaluator refuses to overwrite evidence. Validation also rejects overlapping screen seeds or changed runner/simulation inputs.</p>
<pre>PYTHONPATH=. python scripts/evaluate_card_tactics.py --phase screen --pairs 50 --seed 394000 --workers 4 --output .context/card-tactics-screen.json
PYTHONPATH=. python scripts/evaluate_card_tactics.py --phase validate --pairs 100 --seed 1394000 --workers 4 --selection .context/card-tactics-screen.json --output .context/card-tactics-validation.json
PYTHONPATH=. pytest -q tests/test_card_tactics_evaluation.py
PYTHONPATH=. python scripts/render_tactical_inventory.py
PYTHONPATH=. python scripts/render_card_tactics_guide.py
PYTHONPATH=. python scripts/render_catalog.py
python scripts/check_catalog.py</pre>
<p>The guide renderer reads the committed artifacts; it does not simulate or select policies. The catalog publishes its packaged source and links this guide from the strategy index.</p>
<ul><li><a href="../../scripts/data/card_tactics_screen.json">Raw screen, pre-validation recommendations and scenarios</a></li>
<li><a href="../../scripts/data/card_tactics_validation.json">Raw fresh-validation outcomes, counters and uncertainty</a></li>
<li><a href="../../scripts/evaluate_card_tactics.py">Frozen policies and evaluation runner</a></li>
<li><a href="../../tests/test_card_tactics_evaluation.py">Scenario, reproducibility, evidence and inventory checks</a></li>
<li><a href="../../docs/card-tactical-defaults.md">Developer plan and existing study standards</a></li></ul>''')
    body.append(f'<p class="muted">Python {escape(validation["python_version"])}. Simulation fingerprint: <code>{validation["simulation_fingerprint"]}</code>. Runner SHA-256: <code>{validation["runner_sha256"]}</code>. Screen SHA-256 recorded by validation: <code>{validation["selection_sha256"]}</code>.</p>')
    body.append('</main></body></html>\n')
    return '\n'.join(body)


if __name__ == "__main__":
    SOURCE.write_text(render())
