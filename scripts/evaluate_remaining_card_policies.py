"""Preserve fixed-policy screens and fresh validation for Investment and policy genes."""

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import platform
import random
from statistics import mean

from dominion.ai.genetic_ai import GeneticAI
from dominion.boards.loader import load_board
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.reporting.tournament_state import tournament_fingerprint
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.card_policies import mutate_policies
from dominion.strategy.strategy_loader import StrategyLoader
from scripts import evaluate_card_tactics as original

OPPONENTS = original.OPPONENTS
INVESTMENT_VARIANTS = ('legacy','corrected','uniform_three','min_two','buy_breakpoint','treasure_last','future_trashing')
KINGDOM = original.KINGDOM


@lru_cache(maxsize=1)
def loader():
    return StrategyLoader()


def legacy_mode(self, state, player, can_trash_this):
    if not can_trash_this:
        return 'coin'
    choices = [c for c in player.hand if c.is_treasure]
    picked = self.choose_treasure_to_trash_for_investment(state, player, choices)
    return 'trash' if len({c.name for c in choices if c is not picked}) >= 2 else 'coin'


def subject(study, variant, settings=None, registered=False):
    if registered:
        strategy = loader().get_strategy('lisbon_investment_rush')
    else:
        strategy = original.candidate('Investment','default')
    if study == 'optimizer':
        strategy.gain_priority = [PriorityRule('Province'),PriorityRule('Gold')]+[
            PriorityRule(c, PriorityRule.max_in_deck(c,n)) for c,n in
            [('Investment',2),('Clerk',1),('Bounty Hunter',1),('Watchtower',1),('Smithy',1)]]
        strategy.gain_priority += [PriorityRule('Duchy',PriorityRule.provinces_left('<=',3)),PriorityRule('Silver')]
        strategy.action_priority = [PriorityRule(c) for c in ('Bounty Hunter','Clerk','Watchtower','Smithy')]
        strategy.card_decision_policies = deepcopy(settings)
    elif variant == 'legacy':
        strategy.choose_investment_mode = legacy_mode.__get__(strategy)
    elif variant == 'uniform_three':
        strategy.card_decision_policies = {'investment': {'min_names':3,'duplicate_name_discount':False}}
    elif variant == 'min_two':
        strategy.card_decision_policies = {'investment': {'min_names':2,'duplicate_name_discount':False}}
    elif variant == 'buy_breakpoint':
        strategy.card_decision_policies = {'investment': {'min_names':2,'preserve_buy_breakpoint':True}}
    elif variant == 'treasure_last':
        strategy.treasure_priority = [PriorityRule(c) for c in ('Platinum','Gold','Silver','Copper','Investment')]
    elif variant == 'future_trashing':
        strategy.card_decision_policies = {'investment': {'min_names':3,'future_junk_keep':2,'excess_copy_cashout':3,
                                                         'closing_provinces':1,'closing_names':2}}
        # Preserve economy in the mandatory hand trash unless junk is available.
        strategy.trash_priority = [PriorityRule('Curse'),PriorityRule('Estate')]
    return original.ObservedAI(strategy)


def run_game(spec, variant, settings, seed, seat):
    ours = subject(spec['study'], variant, settings, spec.get('registered',False))
    if spec.get('registered'):
        board = load_board('boards/lisbon.txt')
        kingdom = board.kingdom_cards
        rival = loader().get_strategy(spec['rival'])
    else:
        kingdom = KINGDOM
        rival = original.opponent(spec['rival'])
    other = GeneticAI(rival)
    random.seed(seed)
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game([ours,other] if seat==0 else [other,ours], [get_card(n) for n in kingdom])
    while not state.is_game_over() and state.turn_number < 150:
        state.play_turn()
    a,b = state.players[seat],state.players[1-seat]
    ranks = [(p.get_victory_points(),-p.turns_taken) for p in (a,b)]
    return {'seed':seed,'seat':seat,'policy':variant,'win_share':1 if ranks[0]>ranks[1] else .5 if ranks[0]==ranks[1] else 0,
            'score_margin':ranks[0][0]-ranks[1][0], 'scores':[r[0] for r in ranks],
            'turns_taken':[a.turns_taken,b.turns_taken], 'truncated':not state._normal_game_end_reached(),
            'decisions':dict(ours.decisions)}


def evaluate(task):
    spec, variant, settings, pairs, seed = task
    records=[run_game(spec,variant,settings,seed+i,seat) for i in range(pairs) for seat in (0,1)]
    counts=Counter()
    for r in records: counts.update(r['decisions'])
    return {**spec,'variant':variant,'parameters':settings,'seed_start':seed,'pairs':pairs,
            'win_share':mean(r['win_share'] for r in records),'score_margin':mean(r['score_margin'] for r in records),
            'capped_games':sum(r['truncated'] for r in records),'decisions':dict(counts),'records':records}


def comparisons(rows, control):
    results=[]
    for row in rows:
        if row['variant']==control: continue
        base=next(r for r in rows if r['rival']==row['rival'] and r.get('registered')==row.get('registered') and r['variant']==control)
        records=[{**g,'policy':'contextual'} for g in row['records']]+[{**g,'policy':'default'} for g in base['records']]
        results.append({'variant':row['variant'],'rival':row['rival'],'registered':row.get('registered',False),
                        **original.summarize(records)})
    return results


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',choices=('investment','optimizer'),required=True)
    parser.add_argument('--phase',choices=('screen','validate','registered'),required=True)
    parser.add_argument('--pairs',type=int,default=100)
    parser.add_argument('--seed',type=int,required=True)
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): parser.error('Choose a fresh output path; evidence exists')
    if args.pairs<2 or args.pairs>10000 or args.workers<1 or args.seed<0: parser.error('Invalid pair count, workers or seed')
    fingerprint,runner_hash,helper_hash=tournament_fingerprint(),sha(Path(__file__)),sha(Path(original.__file__))
    population={}
    selection_hash=None
    if args.phase=='validate':
        if not args.selection: parser.error('Validation needs frozen screen selection')
        screen=json.loads(args.selection.read_text())
        if any(screen[k]!=v for k,v in [('study',args.study),('phase','screen'),('simulation_fingerprint',fingerprint),
                                      ('runner_sha256',runner_hash),('summary_helper_sha256',helper_hash)]):
            parser.error('Stale screen inputs')
        population=screen['population'];chosen=screen['selected'];selection_hash=sha(args.selection)
    elif args.selection: parser.error('Only validation accepts selection')
    if args.study=='investment':
        variants=list(INVESTMENT_VARIANTS) if args.phase=='screen' else ['legacy','corrected','uniform_three']
        chosen='corrected'
    elif args.phase=='screen':
        population={'baseline':None}
        rng=random.Random(4132026)
        for i in range(8):
            ai=subject('optimizer','baseline')
            for _ in range(24):mutate_policies(ai.strategy,KINGDOM,1.0,rng)
            population[f'candidate_{i}']=deepcopy(ai.strategy.card_decision_policies)
        variants=list(population)
    else:
        if args.phase=='registered':parser.error('Registered phase is Investment only')
        variants=['baseline',chosen]
    rivals=('city_pile_engine','lisbon_investment_rush','big_money') if args.phase=='registered' else OPPONENTS
    tasks=[]
    for i,rival in enumerate(rivals):
        for variant in variants:
            spec={'study':args.study,'rival':rival,'registered':args.phase=='registered'}
            tasks.append((spec,variant,population.get(variant),args.pairs,args.seed+i*10000))
    if args.phase=='validate':
        previous={g['seed'] for row in screen['rows'] for g in row['records']}
        incoming={seed+i for _,_,_,pairs,seed in tasks for i in range(pairs)}
        if previous & incoming:parser.error('Screen and validation seeds overlap')
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for row in pool.map(evaluate,tasks):
            rows.append(row);print(f"{row['variant']} / {row['rival']}: {row['win_share']:.3f}",flush=True)
    if args.study=='optimizer' and args.phase=='screen':
        chosen=max((v for v in variants if v!='baseline'),key=lambda v:mean(r['win_share'] for r in rows if r['variant']==v))
    if tournament_fingerprint()!=fingerprint or sha(Path(__file__))!=runner_hash or sha(Path(original.__file__))!=helper_hash:
        raise RuntimeError('Inputs changed during study')
    if args.selection and sha(args.selection)!=selection_hash:raise RuntimeError('Screen selection changed')
    control='legacy' if args.study=='investment' else 'baseline'
    varied = {}
    for candidate_settings in population.values():
        for family, values in (candidate_settings or {}).items():
            for key, value in values.items():
                varied.setdefault(f'{family}.{key}', set()).add(value)
    payload={'actual_varied_parameters': {k: sorted(v, key=str) for k,v in varied.items()}, 'study':args.study,'phase':args.phase,'seed':args.seed,'pairs':args.pairs,
             'simulation_fingerprint':fingerprint,'runner_sha256':runner_hash,'summary_helper_sha256':helper_hash,
             'python_version':platform.python_version(),'selection_sha256':selection_hash,'population':population,
             'selected':chosen,'total_games':len(rows)*args.pairs*2,'rows':rows,'comparisons':comparisons(rows,control),
             'selection_rule':'Investment corrected accounting is the predeclared conservative candidate; all ablations screen separately. Optimizer chooses the best mutated candidate by equal-weight mean screen win share; defaults remain unconfigured.',
             'uncertainty':'Seed-clustered 95% Hoeffding bounds; score intervals are paired normal approximations; no multiplicity adjustment.',
             'limitations':'Fixed purchases except declared hand-trash and Treasure-order ablations. Policy genes actually mutate but no purchase genes vary in this benchmark. No strength claim beyond measured panels; equal initial seeds can diverge.'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as out:out.write(json.dumps(payload,indent=2)+'\n')


if __name__=='__main__':main()
