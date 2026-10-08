"""Render the dated free-gain evaluation without rewriting historical evidence."""

import argparse
from html import escape
import json
from pathlib import Path


LABELS = {
    "big_money": "Big Money",
    "big_money_smithy": "Big Money with Smithy",
    "village_smithy_lab": "Village, Smithy, and Laboratory engine",
    "port_moresby_quartermaster_money": "Port Moresby Quartermaster Money",
    "port_moresby_double_quartermaster_money": "Port Moresby Double Quartermaster Money",
    "port_moresby_copper_mat_money": "Port Moresby Copper Mat Money",
    "port_moresby_barbarian_money": "Port Moresby Barbarian Money",
    "port_moresby_falconer_trail_engine": "Port Moresby Falconer Trail Engine",
}


def render(data, historical, previous=None, exports=None, adapters=None, recording=None, policy_audit=None):
    def rate(value, interval):
        return f'{value * 100:.1f}%<small>{interval[0] * 100:.1f}%–{interval[1] * 100:.1f}%</small>'

    def table(rows):
        body = []
        for row in rows:
            label = LABELS[row['strategy']] if 'strategy' in row else (
                row['source'] + (' · independent fallback' if row['independent'] else ' · inherited priorities')
            )
            lo, hi = row['delta_ci']
            body.append(f'<tr><th scope="row">{escape(label)}</th><td>{escape(LABELS[row["opponent"]])}</td>'
                        f'<td>{rate(row["previous_rate"], row["previous_ci"])}</td>'
                        f'<td>{rate(row["current_rate"], row["current_ci"])}</td>'
                        f'<td>{row["delta"] * 100:+.1f}<small>[{lo * 100:+.1f}, {hi * 100:+.1f}]</small></td></tr>')
        return ('<div class="scroll"><table><thead><tr><th scope="col">Strategy / policy</th>'
                '<th scope="col">Opponent</th><th scope="col">Previous win score</th>'
                '<th scope="col">Updated win score</th><th scope="col">Change in percentage points'
                '<small>95% paired interval</small></th></tr></thead><tbody>' + ''.join(body) + '</tbody></table></div>')

    results = data['results']
    diagnostic = [r for r in results if 'source' in r]
    registered = [r for r in results if 'strategy' in r]
    games = sum(r['games_per_policy'] * 2 for r in results)
    truncated = sum(sum(r['truncated']) for r in results)
    findings = []
    for source in ('Workshop', 'Remodel', 'Anvil', 'Quartermaster'):
        rows = [r for r in diagnostic if r['source'] == source]
        supported = [r for r in rows if r['delta_ci'][0] > 0 or r['delta_ci'][1] < 0]
        details = '; '.join(
            f'{"independent fallback" if r["independent"] else "inherited priorities"} versus '
            f'{LABELS[r["opponent"]]}: {r["delta"] * 100:+.1f} points '
            f'[{r["delta_ci"][0] * 100:+.1f}, {r["delta_ci"][1] * 100:+.1f}]'
            for r in supported
        ) or 'all paired intervals span zero'
        findings.append(f'<li><strong>{source}:</strong> {escape(details)}. See all comparisons, including regressions, below.</li>')
    fresh = escape(data['source_fingerprint'])
    old = escape(historical['source_fingerprint'])
    previous_note = (
        '<p>The <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08.json">first October 8 rerun</a>'
        f' is also unchanged, with input fingerprint <code>{escape(previous["source_fingerprint"])}</code>.'
        ' The repeated panels keep broad input provenance exact without relabeling prior runs.</p>'
        if previous is not None else ''
    )
    export_note = (
        '<p>The <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08-exports.json">export-round-trip rerun</a>'
        f' remains unchanged with fingerprint <code>{escape(exports["source_fingerprint"])}</code>.'
        f' The current rerun reproduces {sum(a == b for a, b in zip(results, exports["results"]))}'
        ' of its 33 empirical comparison records. These panels use GeneticAI strategies, so they do not'
        ' measure learned/random adapter performance or imitation training. The current rerun identifies'
        ' the sources after restoring adapter selector control and teacher recording.</p>'
        if exports is not None else ''
    )
    adapter_note = (
        '<p>The <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08-adapters.json">adapter-compatibility rerun</a>'
        f' remains unchanged with fingerprint <code>{escape(adapters["source_fingerprint"])}</code>.'
        ' The recording/discovery rerun below identifies final-gain teacher recording and reusable-strategy'
        ' reference collection, plus an evaluator that refuses existing output paths. These panels do not'
        ' use teacher training or seed retrieval; provenance changes alone do not show performance changes.</p>'
        if adapters is not None else ''
    )
    recording_note = (
        '<p>The <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08-recording.json">recording/discovery rerun</a>'
        f' remains unchanged with fingerprint <code>{escape(recording["source_fingerprint"])}</code>.'
        ' The subsequent policy-propagation audit rerun identified nullable free-gain identity, whole-policy'
        ' crossover, normalization/pruning, baseline-panel deduplication and publication consumers.'
        ' This fixed-policy panel does not test league training or genetic search quality.</p>'
        if recording is not None else ''
    )
    policy_audit_note = (
        '<p>The <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08-policy-audit.json">policy-propagation audit rerun</a>'
        f' remains unchanged with fingerprint <code>{escape(policy_audit["source_fingerprint"])}</code>.'
        ' The current rerun identifies committed-action teacher recording across Workshop, Remodel, Anvil and'
        ' Quartermaster. Its 33 fixed-policy comparison records reproduce the previous panel; this does not'
        ' evaluate imitation training or learned-policy performance.</p>'
        if policy_audit is not None else ''
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Free Gains and Quartermaster: Tactical Policy Evaluation</title>
<style>body{{margin:0;background:#f6f8f8;color:#1c2935;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:auto;padding:36px 24px 72px}}h1{{font:700 2.6rem/1.1 Georgia,serif}}h2{{margin-top:36px}}a{{color:#126b65}}.note{{background:#e6f1ef;border-left:4px solid #126b65;padding:20px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;background:white;font-size:.9rem}}th,td{{padding:12px;text-align:left;border-bottom:1px solid #ced7dd;vertical-align:top}}thead{{background:#e8eef0}}small{{display:block;color:#536270;white-space:nowrap}}code{{overflow-wrap:anywhere}}pre{{background:#e8eef0;padding:16px;overflow:auto}}footer{{margin-top:40px;border-top:1px solid #ced7dd;padding-top:20px}}</style></head><body><main>
<nav><a href="index.html">Strategy catalog</a> · <a href="../../docs/card-tactical-defaults.md">Decision inventory</a></nav>
<h1>Free Gains and Quartermaster: Tactical Policy Evaluation</h1>
<p>Use explicit free-gain preferences or contextual overrides when destinations, sacrifices or hand needs differ from purchases. Generic ranking is a modest fallback; these exploratory comparisons do not establish an optimal policy.</p>
<div class="note"><strong>Dated rerun: October 8, 2026.</strong> {games:,} games across {len(results)} comparisons, {data['pairs']} seed pairs each, four local CPU workers, no model inference. {truncated} games reached the {data['turn_limit']}-round limit. This run uses the merged rules and reviewed fixes. Previous and updated <em>policy arms</em> share the same rerun engine; neither column is the old experiment.</div>
<h2>Run identity and preserved historical evidence</h2>
<p>Rerun simulation input fingerprint: <code>{fresh}</code>. Evaluator SHA-256: <code>{escape(data['evaluator_sha256'])}</code>. Python {escape(data['python_version'])}. The fingerprint covers non-reporting Dominion Python, generated strategies, boards and the tournament configuration files; it identifies inputs, not statistical certainty.</p>
<p>The <a href="../../scripts/data/free_gain_tactics_evaluation.json">original raw outcomes</a> remain byte-for-byte unchanged. Their fingerprint <code>{old}</code> matches the original PR tree <code>4fc860b5b559d85192a97f8535f8a1da31f455f2</code>. They are historical evidence, not results for the reviewed merged tree. All tables and findings below are rendered from the distinct <a href="../../scripts/data/free_gain_tactics_evaluation-2026-10-08-committed-recording.json">October 8 committed-action recording rerun</a>.</p>
{previous_note}
{export_note}
{adapter_note}
{recording_note}
{policy_audit_note}
<p>Since the original run, reviewed inputs changed in exposed-card gain removal, physical-pile endgame context, shared Action/Way resolution and pending bonuses, Anvil validation, opponent trashing/storage defaults, and dynamic board discovery. These can affect legality, choices, random-state progression or opponents. The diagnostic and Port Moresby boards are explicit, so the new free-gain discovery fix does not itself change those boards. Fingerprint changes outside this panel are not evidence that each result changed.</p>
<h2>Practical findings from this rerun</h2><ul>{''.join(findings)}</ul>
<p>Registered Port Moresby strategy changes range from {min(r['delta'] for r in registered) * 100:+.1f} to {max(r['delta'] for r in registered) * 100:+.1f} percentage points. Consult each paired interval below; do not promote a plan on a point estimate alone.</p>
<h2>What was compared</h2>
<p>Each seed runs both policy arms in both seats against the same current opponent. Wins score 1, ties ½, losses 0; equal Victory points are broken by fewer turns taken. The seat scores are averaged before computing uncertainty. Rate intervals use an approximate Wilson bound with a conservative Bernoulli variance bound on independent seed-pair means. Change intervals use paired differences and a normal approximation. Comparisons are unadjusted and exploratory; zero-width intervals from identical observed outcomes do not establish certainty on unseen seeds.</p>
<p>The control adapter freezes previous tactical choices while both arms share corrected costs, gain reactions, Quartermaster replay queues and turn scheduling. This measures policy differences under one engine; it does not estimate the full effect of upgrading the old engine.</p>
<h2>Diagnostic money panels</h2>
<p>Boards contain the tested gainer plus Village, Smithy, Laboratory, Market, Festival, Militia, Moat, Watchtower and Throne Room. Seeds {data['seed']}–{data['seed'] + data['pairs'] - 1}. Inherited priorities retain gain preferences; independent fallback explicitly sets <code>free_gain_priority = []</code>.</p>
{table(diagnostic)}
<h2>Port Moresby: existing strategy reevaluation</h2>
<p>The committed board includes Daimyo, Secluded Shrine, Carpenter, Messenger, Swamp Shacks, Trail, Barbarian, Falconer, Quartermaster and Sculptor, with Seaway and Fountain. Seeds {data['seed'] + 10000}–{data['seed'] + 10000 + data['pairs'] - 1}. The dedicated Copper Mat Money override is retained in both arms.</p>
{table(registered)}
<h2>Rules audit and targeted scenarios</h2>
<p>Regression tests cover mandatory and optional gains, componentwise and modified costs, ownership limits, sacrifice context, Watchtower/Trail reactions, repeated Quartermaster instructions, exposed split-pile depletion, physical-pile menu uniqueness and endgame counts, and existing AI/RL trash hooks. Coverage does not certify every card or landscape interaction. Rules tracking: <a href="https://github.com/jss367/py-overlord/issues/399">Workshop costs</a>, <a href="https://github.com/jss367/py-overlord/issues/400">Remodel costs</a>, and <a href="https://github.com/jss367/py-overlord/issues/401">Quartermaster recurring instructions</a>.</p>
<p>Rule references retained from the original audit: <a href="https://www.riograndegames.com/wp-content/uploads/2013/02/DomAlchemy.pdf">Alchemy</a>, <a href="https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-Empires.pdf">Empires</a>, and <a href="https://www.riograndegames.com/wp-content/uploads/2022/08/DomPlunder.pdf">Plunder</a>. These support the componentwise-cost and Quartermaster rules audit, independently of the empirical policy comparisons.</p>
<h2>Reproduce and inspect the evidence</h2>
<pre><code>PYTHONPATH=. python scripts/evaluate_free_gain_tactics.py --pairs 100 --seed 391000 --workers 4 --output .context/free_gain_tactics_reproduction.json
PYTHONPATH=. python scripts/render_free_gain_tactics_guide.py --results .context/free_gain_tactics_reproduction.json --output .context/free_gain_tactics_reproduction.html
pytest -q tests/test_free_gain_tactics.py tests/test_shared_card_tactics.py tests/test_plunder_kingdom_cards.py
PYTHONPATH=. python scripts/render_catalog.py
python scripts/check_catalog.py</code></pre>
<p>The evaluator refuses an existing output path before starting games and exclusively creates its output. Choose another local filename if the reproduction file already exists. The reproduction renderer reads that new file and writes a separate HTML copy; committed outcomes and the packaged guide remain unchanged. Worker count changes throughput, not seeds. No new free-gain mutation vocabulary was added; crossover can inherit a parent's complete nullable setting, and configured rules participate in normalization and empirical pruning. Saved catalog standings/card ranks are retained with their own freshness notice; this panel does not replace the global tournament.</p>
<footer>Rerun October 8, 2026. <a href="https://github.com/jss367/py-overlord/issues/391">Implementation tracking</a>. Generated from raw outcomes by <a href="../../scripts/render_free_gain_tactics_guide.py">the report renderer</a>.</footer>
</main></body></html>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08-committed-recording.json'))
    parser.add_argument('--historical', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation.json'))
    parser.add_argument('--previous', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08.json'))
    parser.add_argument('--exports', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08-exports.json'))
    parser.add_argument('--adapters', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08-adapters.json'))
    parser.add_argument('--recording', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08-recording.json'))
    parser.add_argument('--policy-audit', type=Path, default=Path('scripts/data/free_gain_tactics_evaluation-2026-10-08-policy-audit.json'))
    parser.add_argument('--output', type=Path, default=Path('dominion/reporting/curated_strategy_guides/free-gains-and-quartermaster-policy-evaluation.html'))
    args = parser.parse_args()
    args.output.write_text(render(json.loads(args.results.read_text()), json.loads(args.historical.read_text()), json.loads(args.previous.read_text()), json.loads(args.exports.read_text()), json.loads(args.adapters.read_text()), json.loads(args.recording.read_text()), json.loads(args.policy_audit.read_text())))


if __name__ == '__main__':
    main()
