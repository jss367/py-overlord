"""Publish a completed saved-candidate diagnostic as an HTML strategy guide."""

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import shutil
from statistics import mean

from scripts.compare_saved_reflective_candidates import ARMS, LABELS, analyze, panel_mean


def percent(value):
    return f"{100 * value:.1f}%"


def points(value):
    return f"{100 * value:+.1f}"


def table(headers, rows):
    return ('<div class="table"><table><thead><tr>'
            + ''.join(f'<th scope="col">{escape(str(h))}</th>' for h in headers)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{escape(str(c))}</td>' for c in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def direct_rate(result, left, right):
    left, right = result["aliases"][left], result["aliases"][right]
    if left == right:
        return "Identical policy"
    forward = result["direct"].get(f"{left}_vs_{right}")
    rate = forward["win_rate"] if forward is not None else 1 - result["direct"][f"{right}_vs_{left}"]["win_rate"]
    return percent(rate)


def render_guide(report, *, board_name, evidence_name):
    if report["status"] != "complete" or report["analysis"] != analyze(report["results"]):
        raise ValueError("A complete report with consistent analysis is required")
    analysis, results = report["analysis"], report["results"]
    effect = analysis["panel_differences"]["assisted_minus_proposal"]
    low, high = effect["ci95"]
    verdict = ("Final assisted recommendations improved on the original proposals across these runs."
               if low > 0 else "Original proposals outperformed the final assisted recommendations across these runs."
               if high < 0 else "The study did not resolve a consistent benefit from further genetic search.")
    seed_rows = []
    for result in results:
        rates = {arm: panel_mean(result["panels"][result["aliases"][arm]]) for arm in ARMS}
        seed_rows.append([result["seed"], *[percent(rates[arm]) for arm in ARMS],
                          points(rates["assisted"] - rates["proposal"]),
                          "Yes" if result["aliases"]["assisted"] == result["aliases"]["proposal"] else "No"])
    opponent_rows = []
    for name in report["opponents"]:
        rates = [mean(next(m["win_rate"] for m in r["panels"][r["aliases"][arm]]["matchups"]
                           if m["case"]["opponent"] == name) for r in results) for arm in ARMS]
        opponent_rows.append([name, *map(percent, rates), points(rates[1] - rates[0])])
    direct_rows = [[r["seed"], direct_rate(r, "assisted", "proposal"),
                    direct_rate(r, "proposal", "control"), direct_rate(r, "assisted", "control")]
                   for r in results]
    difference_rows = [[LABELS[left] + " minus " + LABELS[right], points(value["mean"]),
                        f"{points(value['ci95'][0])} to {points(value['ci95'][1])}"]
                       for key, value in analysis["panel_differences"].items()
                       for left, right in [key.split("_minus_")]]
    candidate_rows = [[r["seed"], LABELS[arm], r["selected_names"][r["aliases"][arm]]]
                      for r in results for arm in ARMS]
    title = f"{board_name}: Reflective Proposals and Final Search Recommendations"
    escaped_title = escape(title)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escaped_title}</title>
<meta name="description" content="Fresh seat-balanced comparisons of saved reflective proposals, final assisted recommendations and genetic-only controls, with search-run uncertainty.">
<style>
:root{{color-scheme:light;--ink:#183229;--muted:#56695f;--line:#d5dfd8;--accent:#12694a}}
*{{box-sizing:border-box}}body{{margin:0;background:#f7faf7;color:var(--ink);font:16px/1.65 system-ui,sans-serif}}
main{{max-width:1120px;margin:auto;padding:32px 24px 64px}}a{{color:var(--accent)}}
h1{{font-size:clamp(2rem,5vw,3.5rem);line-height:1.12;max-width:28ch}}h2{{margin-top:38px}}
p,li{{max-width:92ch}}.muted{{color:var(--muted)}}.verdict{{padding:24px;background:#e5f1e7;border:1px solid #b6d4bf;border-radius:12px}}
.verdict strong{{font-size:1.3rem}}.table{{overflow:auto;border:1px solid var(--line);border-radius:10px;margin:24px 0}}
table{{width:100%;border-collapse:collapse;background:white}}th,td{{padding:12px 16px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}}th{{background:#edf3ee}}
pre{{padding:20px;background:#edf3ee;white-space:pre-wrap;overflow-wrap:anywhere;border-radius:10px}}code{{font-size:.9em;overflow-wrap:anywhere}}
footer{{margin-top:40px;color:var(--muted)}}
</style></head><body><main>
<nav><a href="index.html">Strategy catalog</a> · <a href="oslo-reflective-shared-budget-benchmark.html">Original equal-budget benchmark</a></nav>
<p class="muted">{date.today().isoformat()} · Saved-candidate diagnostic · {len(results)} search runs</p>
<h1>{escaped_title}</h1>
<div class="verdict"><strong>{escape(verdict)}</strong>
<p>The original GEPA proposals averaged {percent(analysis['panel_means']['proposal'])} wins against the five-opponent panel;
the final assisted recommendations averaged {percent(analysis['panel_means']['assisted'])}, and genetic-only controls
averaged {percent(analysis['panel_means']['control'])}.</p>
<p>Final recommendations changed the panel win rate by {points(effect['mean'])} percentage points versus their proposals
(95% interval across search runs: {points(low)} to {points(high)} points).
{analysis['unchanged_proposals']} of {len(results)} final recommendations were identical to their original proposals.</p></div>
<p>This follow-up reused the five saved runs from the <a href="oslo-reflective-shared-budget-benchmark.html">shared-budget benchmark</a>.
GEPA is the reflective optimization method that revised typed strategy plans using simulator feedback.
The original proposal is GEPA's selected plan before genetic training. The final assisted recommendation was selected
from the assisted search's starting policies and genetic champion. It can be a different starting policy or a mutation;
this comparison does not establish ancestry from the proposal.</p>
<h2>Fresh opponent-panel results</h2>
{table(['Search seed', 'Original proposal', 'Final assisted', 'Genetic control', 'Change in percentage points', 'Proposal retained?'], seed_rows)}
<p>Each distinct candidate played {report['games_per_matchup']:,} games against each of the same five opponents.
Every shuffle seed was played in both seats. Candidates shared shuffle seeds within each opponent matchup.
All policies were frozen before any new games, and the new outcomes did not select or alter a recommendation.</p>
{table(['Opponent', 'Original proposal', 'Final assisted', 'Genetic control', 'Change in percentage points'], opponent_rows)}
<h2>Uncertainty across search runs</h2>
{table(['Panel comparison', 'Mean change in percentage points', '95% interval in percentage points'], difference_rows)}
<p>The primary analysis was the paired change in ordinary opponent-panel mean, final assisted minus original proposal.
It was written to the run manifest before evaluation. Two-sided Student-t intervals use the {len(results)} search runs
as observations, including exact zero differences when the final policy equals the proposal. Games and seat pairs
are not treated as independent search replications. These approximate intervals are wide with only five runs;
secondary comparisons are descriptive and have no multiple-comparison correction.</p>
<h2>Direct pairwise games</h2>
{table(['Search seed', 'Final wins vs proposal', 'Proposal wins vs control', 'Final wins vs control'], direct_rows)}
<p>Each distinct pair played {report['games_per_matchup']:,} games on a separate fresh block, with both seats.
Direct pairs within a search run shared their shuffle block. Identical policies were not played against themselves;
their panel and control-matchup results were reused. Percentages use the simulator's winner, including its
seat-order fallback when points and turn counts are fully tied.</p>
<h2>What this tells us about the next experiment</h2>
<p>This diagnostic measures the quality of particular saved proposals and recommendations. It does not compare
equally funded GEPA-only and assisted algorithms: the original proposals consumed much less search computation,
and the assisted procedure can fall back to another starting seed. The runs were inspected in the previous study,
so this is a post-hoc follow-up with fresh shuffle evidence, rather than five new independent search runs.</p>
<p>The next algorithm comparison should give a proposal-only arm its own explicit budget for additional reflective
proposals and validation, then compare it with assisted and genetic-only arms on new search seeds. Keep all three
recommendations eligible during validation and lock them before a separate test block. Additional kingdoms are
needed before choosing a general default; these findings apply to the Oslo board and this policy representation.</p>
<h2>Evidence and reproduction</h2>
<p>The comparison completed {analysis['total_simulated_games']:,} fresh games with no model requests.
<a href="../research/{escape(evidence_name)}">Download all outcomes, seeds, seats, candidate hashes and analysis</a>.
The <a href="../research/oslo-reflective-shared-budget-benchmark.json">original benchmark evidence</a> preserves the
proposed JSON plans and final rule lists. The local run folder contains frozen trusted checkpoints, opponents and
a snapshot of the evaluator command. Raw game arrays have named columns.</p>
<p>The runner checked its new shuffle seeds against {report['freshness_check']['recorded_source_shuffle_seeds']:,}
distinct saved source-game seeds, with zero overlap. That covers saved reflection, selection and held-out games;
genetic training's unsaved game seeds could not be enumerated. New cases use a separate hashed seed namespace.
The simulator input fingerprint matched the original benchmark before and after evaluation.</p>
<pre><code>PYTHONPATH=. python scripts/compare_saved_reflective_candidates.py \\
  --source .context/oslo-reflective-shared-budget-benchmark \\
  --games {report['games_per_matchup']} --workers {report['workers']} \\
  --output .context/oslo-saved-candidate-reproduction</code></pre>
<p>This command requires the trusted local checkpoints from the earlier experiment. Pickle checkpoints are executable
Python data and must not be loaded from an untrusted source. A clean clone has the public evidence, but not the
gitignored checkpoints. Re-running the original live reflective search can produce different proposals.</p>
<details><summary>Locked candidate names for traceability</summary>{table(['Search seed', 'Candidate', 'Saved name'], candidate_rows)}</details>
<footer>Simulation fingerprint: <code>{escape(report['simulation_fingerprint'])}</code>.
No saved standings or runnable catalog strategies were changed by this diagnostic.</footer>
</main></body></html>'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--guide", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--board-name", default="Oslo")
    args = parser.parse_args()
    report = json.loads(args.comparison.read_text())
    html = render_guide(report, board_name=args.board_name, evidence_name=args.evidence.name)
    args.guide.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.guide.write_text(html)
    shutil.copyfile(args.comparison, args.evidence)
    print(f"Published guide source: {args.guide}")


if __name__ == "__main__":
    main()
