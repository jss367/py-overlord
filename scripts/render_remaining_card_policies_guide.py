"""Publish the frozen gain-ordering and bounded card-policy studies as HTML."""

from collections import Counter
from html import escape
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.card_policies import POLICY_DOMAINS

NAME = 'gain-effect-ordering-and-searchable-card-policies.html'
TITLE = 'Ordering Gain Effects and Searching Card Policies'
DATA = Path('scripts/data')
SOURCE = Path('dominion/reporting/curated_strategy_guides') / NAME


def table(headers, rows):
    return '<div class="table-scroll"><table><thead><tr>' + ''.join(
        f'<th>{escape(h)}</th>' for h in headers
    ) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join(
        f'<td>{escape(str(v))}</td>' for v in row
    ) + '</tr>' for row in rows) + '</tbody></table></div>'


def bounds(values, scale=1):
    return f'[{values[0] * scale:+.2f}, {values[1] * scale:+.2f}]'


def caps_sensitivity(records):
    """Keep both seats/policies paired; report uncapped blocks and cap ranges."""
    complete = [r for r in records if not any(s['turn_limit'] for arm in r for s in arm)]
    delta = mean(mean(s['win_share'] for s in r[1]) - mean(s['win_share'] for s in r[0]) for r in complete) if complete else None
    lo = mean(mean(0 if s['turn_limit'] else s['win_share'] for s in r[1]) - mean(1 if s['turn_limit'] else s['win_share'] for s in r[0]) for r in records)
    hi = mean(mean(1 if s['turn_limit'] else s['win_share'] for s in r[1]) - mean(0 if s['turn_limit'] else s['win_share'] for s in r[0]) for r in records)
    return len(complete), 'none' if delta is None else f'{delta * 100:+.1f}', bounds([lo, hi], 100)


def render():
    names = ('investment-accounting-screen', 'investment-accounting-validation',
             'investment-registered-validation', 'contextual-policy-search-screen',
             'contextual-policy-search-validation', 'gain-effect-ordering-reaction-validation')
    studies = [json.loads((DATA / (n + '.json')).read_text()) for n in names]
    screen, validation, registered, search, heldout, reactions = studies
    fingerprint = tournament_fingerprint()
    for study in studies:
        if study.get('simulation_fingerprint', study.get('source_fingerprint')) != fingerprint:
            raise ValueError('Study uses different simulation inputs')
    for study, previous in ((validation, names[0]), (heldout, names[3])):
        if study['selection_sha256'] != hashlib.sha256((DATA / (previous + '.json')).read_bytes()).hexdigest():
            raise ValueError('Validation selection hash mismatch')
    for study in studies[:5]:
        if study['runner_sha256'] != hashlib.sha256(Path('scripts/evaluate_remaining_card_policies.py').read_bytes()).hexdigest():
            raise ValueError('Policy runner changed')
    css = Path('dominion/reporting/curated_strategy_guides/card-reactions-investment-and-exile-evaluation.html').read_text().split('<style>')[1].split('</style>')[0]
    body = [f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{TITLE}</title><style>{css}</style></head><body><main>',
            f'<p><a href="index.html">Strategy catalog</a> · <a href="../../docs/card-tactical-inventory.md">Card evidence inventory</a></p><h1>{TITLE}</h1>',
            f'<p class="muted">October 14, 2026 · {sum(s.get("total_games", s.get("games", 0)) for s in studies):,} games · Scoped rules corrections and fresh policy comparisons</p>',
            '''<div class="recommendation"><strong>Use owner-ordered gain effects and accurate Investment accounting; keep the conservative tactical defaults.</strong> The engine now offers legal effect order to each owner and refreshes hand reactions after each resolution. Investment values every live Treasure name left after its mandatory hand trash. Optional finite policy settings can mutate and export. The selected search candidate shows no observed validation improvement; a uniform three-name cash-out rule regresses and is rejected.</div>
<p>This closes the implementation scope of <a href="https://github.com/jss367/py-overlord/issues/410">simultaneous gain ordering</a>, <a href="https://github.com/jss367/py-overlord/issues/411">Investment accounting and timing evaluation</a> and <a href="https://github.com/jss367/py-overlord/issues/413">searchable contextual decisions</a>. The <a href="https://github.com/jss367/py-overlord/issues/344">broader card inventory</a> remains open. Rules scenarios, connected hooks and measured strength are separate claims. These experiments rerun scoped contrasts on the current engine; historical studies and global standings retain their original evidence.</p>
<h2>What changes during a gain</h2>
<p>The real turn player resolves their effects first, followed by other owners in turn order. Each owner chooses one offered effect with <code>choose_gain_effect(state, player, gained_card, choices)</code>. Choices are objects with <code>kind</code>, <code>source</code> and a readable <code>label</code>. Return an offered object or its kind string; invalid results use the first legal choice. Existing card-specific decisions still decide whether to react. Returning no ordering choice does not decline all effects.</p>
<p>Active instructions are captured when the gain occurs. Newly drawn hand reactions can join after each effect. Each physical hand reaction is offered at most once per gain, and the selected instruction is consumed before nested gains run. A 256-effect guard raises an error for pathological custom chains. Once-per-event instructions, gain counts, gain-time costs and types are reserved before nested effects can change them. The choice hook and resolution both run with the effect owner's current-player context while preserving the real turn player.</p>
<p>Sleigh can resolve before or after Sheepdog. Additional Sleighs can be discarded for their discard effects even after the gained card stops moving. Watchtower, Cargo Ship, Innovation, Deliver, Sailor and other movers respect the original destination. Moving a gain to another zone prevents later movers from following it; topdecking a card already on top of its original deck does not change zones. Covering a gained deck card stops its movement even if a nested gain subsequently removes the covering card. Landing Party instructions cannot recreate a trashed physical card or a virtual Supply proxy.</p>
<p>Regression scenarios include both Sleigh/Sheepdog orders, newly drawn reactions, multiple Sleigh discards with nested gains, Watchtower movement, covered deck cards, Cargo Ship competition, off-turn ownership, gain counters and reserved instructions, live type changes, Landing Party source ownership and copied player-ID maps. This is a scoped audit of the common event path, not certification of every Dominion interaction.</p>
<p>The designer's <a href="https://dominionstrategy.com/2019/09/25/dominion-2019-errata-and-rules-tweaks/">stop-moving clarification</a> defines expected gain locations and covered deck cards. The publisher's <a href="https://www.riograndegames.com/wp-content/uploads/2020/01/DominionMenagerie.pdf">Menagerie rules</a> explain newly drawn Sheepdog reactions; the <a href="https://www.riograndegames.com/wp-content/uploads/2022/03/Dominion-Rules-Empires.pdf">Empires rules</a> explain simultaneous effects across owners.</p>
<h2>Investment counts the actual remaining hand</h2>
<p>Investment first trashes a hand card, then chooses +$1 or self-trash. Self-trash awards one point per differently named live Treasure remaining in hand; Investment is not a second selected hand Treasure. The decision and scoring use the same live-type helper, including Capitalism, Charlatan and Inheritance interactions. If Investment cannot trash itself, the mode remains money.</p>
<p>The corrected inherited strategy compares actual points with a conservative threshold of three names, discounted to two when the weakest live Treasure name is repeated. Copper is the weakest name when present; otherwise printed cost and name break ties. This preserves the legacy decisions on ordinary Treasure hands without pretending to remove a hand card. Tests exhaust ordinary Copper/Silver/Gold/Investment multisets through six cards. Explicit mode overrides still take precedence. The old Treasure-selection method remains callable for compatibility and is documented as unused by the card engine; the historical keyword spelling of the self-trash flag remains accepted.</p>
<p>Counting two real points does not by itself prove that cashing out now is best. The screen separately varies a uniform three-name rule, two-name rule, buy-breakpoint protection, Treasure play order, mandatory hand-trash priorities, future junk retention, excessive-copy cash-out and closing points. The latter three are separate ablations; they are not bundled with the hand-trash change. The corrected compatibility policy was the predeclared production candidate, locked before fresh validation. No diagnostic late-only policy is promoted.</p>
<h2>Finite settings available to search</h2>
<p><code>card_decision_policies=None</code> inherits; <code>{}</code> declares no family overrides and remains distinct in signatures and exports. An omitted field inherits that family's fallback. The complete finite vocabulary is below. Unknown keys, out-of-domain values and bool/integer substitutions are rejected. Configuring a Watchtower family enables its fallback hand and terminal limits of eight and six unless explicitly set.</p>''']
    meanings = {
        'watchtower': 'Keep Copper below owned live-Treasure printed income; minimum gain cost for topdeck; terminal-Action ownership and current hand limits.',
        'clerk': 'Prefer non-Action/non-Treasure Victory cards for the victim topdeck; choose whether to play the start-turn reaction.',
        'investment': 'Minimum distinct names; repeated-weakest-name discount; closing point threshold and Province/Colony pile limit; protect the next $5/$6/$8/$11 buy; keep future hand trashing while junk remains; cash out excessive owned copies.',
        'bounty_hunter': 'Prefer fresh eligible names; prioritize a +$3 crossing the selected buy price after losing the exiled card; retain useful names at or below the owned-copy threshold. Junk and Victory names remain eligible.',
        'gain_order': 'Prefer one available simultaneous-effect kind; all remaining effects retain the legal fallback order.',
    }
    body.append(table(('Family', 'Allowed parameter values', 'Meaning'), [(family, '; '.join(f'{k} = {v}' for k, v in fields.items()), meanings[family]) for family, fields in POLICY_DOMAINS.items()]))
    body += ['''<p>Typed genome promotion, compilation, synchronization, native mutation and crossover preserve nullable settings and copy mappings without aliasing. Python export and strategy discovery retain settings and card references. Explicit Bounty Hunter exile priorities and custom callable hooks remain authoritative. Existing purchase, supply-play, free-gain and trash rules are independent; arbitrary Python functions are not converted into genes. Income breakpoints use printed money in the current live-Treasure hand, not a forecast of all future Action effects.</p>
<pre>strategy.card_decision_policies = {
    "gain_order": {"first": "sheepdog"},
    "investment": {"min_names": 2, "preserve_buy_breakpoint": True},
    "clerk": {"dead_cards_first": True, "play_at_start": False},
}</pre>
<p>This example demonstrates the vocabulary, not a strength recommendation. Gain-order preference is tested through physical scenarios; the optimizer panel below has no Sleigh, Sheepdog or Cargo Ship, so it does not mutate that family.</p>
<h2>Boards, selection and uncertainty</h2>
<p>The Investment and optimizer panels use Watchtower, Clerk, Investment, Bounty Hunter, Village, Smithy, Laboratory, Witch, Militia and Moat, standard starting decks and no landscapes. The three opponents are Smithy money, a Village/Laboratory engine and a Clerk/Witch attack. The engine is weak on this board and lacks its preferred Chapel. Investment purchases and play order follow the historical fixed subject: Province, Gold, up to two Investments, one Smithy, late Duchy, Silver, late Estate; Investment plays before Gold, Silver and Copper. Hand trash prefers Curse, eligible Estate, then Copper above $4 owned printed Treasure income. Only the named hand-trash or play-order ablation changes those choices.</p>
<p>The optimizer adds up to one Clerk, Bounty Hunter and Watchtower, with Action order Bounty Hunter, Clerk, Watchtower, Smithy. Eight candidates receive 24 calls each to production tactical mutation with a fixed local random seed. The unconfigured baseline is also evaluated. Purchase genes do not vary. Selection maximizes equal-weight average screen win share among mutated candidates, with deterministic tie-breaking. This is a bounded mutation screen that exercises production genes, not a full evolutionary purchase-and-policy tournament.</p>
<p>Investment uses 30 screen seeds and 100 fresh validation seeds, both seats. The optimizer uses 20 screen seeds and 100 fresh validation seeds. Validation loads the frozen screen hash and rejects changed inputs or overlapping seeds. Wins score 1, ties ½, losses 0, with fewer turns taken breaking equal physical scores. Both seats are averaged within each independent seed block. Conservative 95% Hoeffding bounds for paired win-share changes have radius ±27.16 percentage points at 100 seeds (±49.59 at 30; ±60.74 at 20). Score-change intervals are paired normal approximations. All are per-comparison and exploratory, without multiplicity adjustment. Equal initial seeds can diverge after different decisions.</p>''']
    for heading, study in (('Investment screen: isolated alternatives', screen), ('Investment fresh validation', validation), ('Registered Investment strategy on Lisbon', registered)):
        body.append(f'<h2>{heading}</h2>')
        body.append(table(('Policy', 'Opponent', 'Control win share', 'Policy win share', 'Change (points)', '95% change bound (points)', 'Score-margin change', 'Approximate score-change interval'), [
            (r['variant'], r['rival'], f'{r["policies"]["default"]["win_share"]:.1%}', f'{r["policies"]["contextual"]["win_share"]:.1%}', f'{r["win_share_delta"] * 100:+.1f}', bounds(r['delta_95_interval'], 100), f'{r["score_margin_delta"]:+.2f}', bounds(r['score_delta_approximate_95_interval'])) for r in study['comparisons']]))
    body += ['''<p>The uniform three-name rule loses 6.5, 5.5 and 10.5 percentage points in fresh fixed-board validation. All three approximate score-change intervals are negative; conservative win-share bounds still include zero. The corrected compatibility policy matches the legacy control exactly in these ordinary-hand games. Live-type changes are covered by physical tests, not these no-landscape benchmarks.</p>
<p>The registered Investment factory discovered by the loader is Lisbon Investment Rush. Its own Lisbon board includes Colony and Platinum. It is compared against City Pile Engine, itself and Big Money. The mirror has substantial 150-turn truncation; reported provisional wins and score margins are not complete-game evidence. The cap table below gives both policies' capped counts, a worst-case range obtained by assigning every capped outcome either a loss or a win, and a sensitivity estimate using only seed blocks where both seats and both policies ended normally. The latter conditions on completion and is not an unbiased full-panel estimate.</p>''']
    cap_rows = []
    for r in registered['comparisons']:
        a = next(row for row in registered['rows'] if row['rival'] == r['rival'] and row['variant'] == 'legacy')
        b = next(row for row in registered['rows'] if row['rival'] == r['rival'] and row['variant'] == r['variant'])
        blocks = [[[{'win_share': g['win_share'], 'turn_limit': g['truncated']} for g in arm['records'][i:i+2]] for arm in (a, b)] for i in range(0, len(a['records']), 2)]
        n, delta, possible = caps_sensitivity(blocks)
        cap_rows.append((r['variant'], r['rival'], f'{a["capped_games"]} / {b["capped_games"]}', possible, n, delta))
    body.append(table(('Policy', 'Opponent', 'Capped games: control / policy (200 each)', 'Worst-case capped change range (points)', 'Complete paired seed blocks', 'Complete-block change (points)'), cap_rows))
    body.append('<h2>Optimizer screen and frozen validation</h2>')
    body.append(table(('Screen candidate', 'Mean win share across opponents', 'Settings'), [(v, f'{mean(r["win_share"] for r in search["rows"] if r["variant"] == v):.1%}', json.dumps(settings, sort_keys=True)) for v, settings in search['population'].items()]))
    body.append(f'<p>The locked selection is <code>{escape(search["selected"])}</code>. Its actual validation settings are recorded below. The inherited baseline remains the default because no improvement is established.</p>')
    body.append(table(('Opponent', 'Baseline win share', 'Selected win share', 'Change (points)', '95% change bound (points)', 'Score-margin change'), [(r['rival'], f'{r["policies"]["default"]["win_share"]:.1%}', f'{r["policies"]["contextual"]["win_share"]:.1%}', f'{r["win_share_delta"] * 100:+.1f}', bounds(r['delta_95_interval'], 100), f'{r["score_margin_delta"]:+.2f}') for r in heldout['comparisons']]))
    body.append('<details><summary>Actual varied fields in the evaluated screen population</summary>' + table(('Parameter', 'Observed settings (inherit means omitted)'), search['actual_varied_parameters'].items()) + '</details>')
    body.append('<p>Validation compares only the selected genotype with the baseline; its raw artifact records that smaller actual field set. Hook counters establish that choices execute; unchanged or inactive settings can still tie on this board. Candidate settings, raw games, rejected regressions and every decision counter are preserved. No stronger timing policy or universal recommendation follows from this screen.</p>')
    counts = Counter()
    for row in heldout['rows']:
        counts.update(row['decisions'])
    body.append('<details><summary>Validation decision firings across both policies</summary>' + table(('Choice / response', 'Firings'), sorted(counts.items())) + '</details>')
    body.append('''<h2>Reaction and Duration contrasts on the corrected gain engine</h2>
<p>The historical Barge/Sleigh/Torturer runner is rerun at 100 fresh seeds, both seats, for four fixed subjects against Big Money, Smithy money and a Torturer opponent. Six affected registered strategies are also rerun on their original boards against both money opponents. Both policy arms use the corrected gain engine and current opponents; this measures the historical tactical contrast under new rules, not the causal effect of this engine patch. Candidate ordering policies are held at the fallback. Barge and Torturer can change simultaneously with Sleigh, so results do not isolate a single reaction gene.</p>
<p>The fixed board is Barge, Sleigh, Torturer, Village, Workshop, Smithy, Militia, Chapel, Market and Watchtower. Registered boards, landscapes and kingdoms are recorded per row. The legacy comparison always resolves Barge immediately and moves qualifying Sleigh gains to hand; the current comparison uses shared Barge timing, Sleigh destination and Torturer choices. Historical rejected purchase-preserving Torturer studies are not promoted or overwritten.</p>''')
    rows = []
    capped_reactions = []
    for r in reactions['results']:
        radius = 2 * math.sqrt(math.log(40) / (2 * r['seed_pairs']))
        rows.append((r.get('candidate', r.get('strategy')), r['opponent'], f'{r["previous_win_share"]:.1%}', f'{r["current_win_share"]:.1%}', f'{r["difference"] * 100:+.1f}', bounds([max(-1, r['difference']-radius), min(1, r['difference']+radius)], 100), f'{r["score_margin_difference"]:+.2f}', str(r['turn_limit_games'])))
        if any(r['turn_limit_games']):
            n, delta, possible = caps_sensitivity(r['per_seed_outcomes'])
            capped_reactions.append((r.get('candidate', r.get('strategy')), r['opponent'], possible, n, delta))
    body.append(table(('Subject', 'Opponent', 'Previous win share', 'Current win share', 'Change (points)', '95% conservative bound (points)', 'Score-margin change', 'Capped games: previous/current'), rows))
    body.append('<p>The guide recomputes conservative Hoeffding change bounds from the saved seed blocks. The legacy runner also saves approximate paired intervals that can collapse at zero observed variance; those are not evidence of exact equivalence. Full scores, counters, cap flags and paired outcomes remain in the raw artifact. No full global tournament was run.</p>')
    if capped_reactions:
        body.append('<h3>Capped reaction contrasts: sensitivity</h3>' + table(('Subject', 'Opponent', 'Worst-case capped change range (points)', 'Complete paired seed blocks', 'Complete-block change (points)'), capped_reactions))
    body.append('<h2>Reproduction and source evidence</h2><p>Use fresh output paths; the runners refuse to overwrite existing evidence. These commands use the committed final inputs. The guide renderer validates simulation and selection provenance without simulating games.</p><pre>')
    commands = [
        f'PYTHONPATH=. python scripts/evaluate_remaining_card_policies.py --study {study} --phase {phase} --pairs {pairs} --seed {seed} --workers 4' + (f' --selection .context/{selection}.json' if selection else '') + f' --output .context/{name}.json'
        for study, phase, pairs, seed, selection, name in (
            ('investment','screen',30,14110000,None,names[0]), ('investment','validate',100,16110000,names[0],names[1]),
            ('investment','registered',100,18110000,None,names[2]), ('optimizer','screen',20,14130000,None,names[3]),
            ('optimizer','validate',100,16130000,names[3],names[4]))]
    commands += [f'PYTHONPATH=. python scripts/evaluate_reaction_duration_tactics.py --pairs 100 --seed 4410000 --workers 4 --output .context/{names[5]}.json', 'PYTHONPATH=. python scripts/render_remaining_card_policies_guide.py', 'PYTHONPATH=. python scripts/render_tactical_inventory.py', 'PYTHONPATH=. python scripts/render_catalog.py', 'pytest -q', 'python -m ruff check .', 'python scripts/check_catalog.py']
    body.append(escape('\n'.join(commands)) + '</pre><ul>')
    for name in names:
        body.append(f'<li><a href="../../scripts/data/{name}.json">{escape(name.replace("-", " "))}: frozen raw evidence</a></li>')
    body += ['''<li><a href="../../scripts/evaluate_remaining_card_policies.py">Policy benchmark and predeclared selection protocol</a></li>
<li><a href="../../dominion/strategy/card_policies.py">Finite policy vocabulary and Investment accounting</a></li>
<li><a href="../../dominion/game/gain_effects.py">Owner-ordered gain event implementation</a></li>
<li><a href="../../tests/test_gain_effect_ordering.py">Physical gain-order scenarios</a></li>
<li><a href="../../tests/test_searchable_card_policies.py">Genome, mutation, override, export and live-type checks</a></li>
<li><a href="../../tests/test_remaining_policy_protocol.py">Stale-input, overlap and overwrite rejection checks</a></li></ul>''',
             f'<p class="muted">Python {validation["python_version"]}. Simulation fingerprint: <code>{fingerprint}</code>. Policy runner SHA-256: <code>{validation["runner_sha256"]}</code>. Every artifact retains its runner and input provenance.</p></main></body></html>']
    SOURCE.write_text('\n'.join(body) + '\n')


if __name__ == '__main__':
    render()
