"""League rounds retain discovered strategies on both sides of a comparison."""

from copy import deepcopy

import pytest

from dominion.boards.loader import BoardConfig
from dominion.simulation.adversarial_league import AdversarialLeague, ORIGIN_SEED
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy
from scripts import league_evolve


def strategy(name, card):
    result = BaseStrategy()
    result.name = name
    result.gain_priority = [PriorityRule(card)]
    return result


@pytest.mark.parametrize('use_league', [True, False])
def test_later_rounds_inherit_previous_champion(monkeypatch, use_league):
    trainers = []
    champions = [strategy('First champion', 'Gold'), strategy('Second champion', 'Silver')]
    engine = strategy('Engine', 'Village')
    reference = strategy('Reference', 'Smithy')
    league = AdversarialLeague(capacity=5) if use_league else None
    if league is not None:
        league.add(reference, name=reference.name, origin=ORIGIN_SEED)

    class Trainer:
        def __init__(self, **kwargs):
            self.injected = []
            self.best_eval_breakdown = []
            trainers.append(self)

        def inject_strategy(self, candidate):
            self.injected.append(candidate)

        def train(self):
            return deepcopy(champions[len(trainers) - 1]), {'fitness': 50, 'win_rate': 50}

    monkeypatch.setattr(league_evolve, 'GeneticTrainer', Trainer)
    monkeypatch.setattr(league_evolve, 'build_engine_seeds', lambda *a, **k: [('Engine', engine)])
    league_evolve.run_rounds(
        BoardConfig(['Village', 'Smithy']), league,
        rounds=2, worst_case_weight=0.5, inject_engine_seeds=True,
        max_engines=1, eval_seed=1, trainer_kwargs={},
    )
    assert [s.name for s in trainers[0].injected] == ['Engine']
    carried = trainers[1].injected
    assert carried[0].name == 'First champion'
    assert carried[0] is not champions[0]
    assert [r.card_name for s in carried for r in s.gain_priority].count('Gold') == 1
    assert ('Reference' in [s.name for s in carried]) == use_league
    carried[0].gain_priority.clear()
    assert champions[0].gain_priority


@pytest.mark.parametrize("wins,losses,ties,truncated,rate", [
    (0, 0, 200, 0, 50.0),
    (0, 0, 0, 200, 0.0),
    (40, 20, 60, 80, 35.0),
    (120, 80, 0, 0, 60.0),
])
def test_reference_gate_uses_win_shares_and_retains_outcome_counts(monkeypatch, wins, losses, ties, truncated, rate):
    """Feed summaries directly; no battle or evolutionary evaluation executes."""
    from types import SimpleNamespace
    from dominion.analysis.calibration import wilson_interval

    result = {"strategy1_wins": wins, "strategy2_wins": losses,
              "ties": ties, "truncated": truncated, "strategy1_win_rate": rate}
    closed = []

    class Battle:
        def __init__(self, **kwargs):
            self.strategy_loader = SimpleNamespace()

        def run_battle(self, first, second, games):
            assert (first, second, games) == ("Candidate", "Reference", 200)
            return result

        def close(self):
            closed.append(True)

    monkeypatch.setattr(league_evolve, "StrategyBattle", Battle)
    row = league_evolve.head_to_head(BoardConfig(["Village"]), "Candidate", None, "Reference", None, 200)
    assert closed == [True]
    assert row["win_rate"] == rate
    assert (row["wins"], row["losses"], row["ties"], row["truncated"]) == (wins, losses, ties, truncated)
    assert row["ci"][0] <= rate <= row["ci"][1]
    if ties or truncated:
        assert row["interval_method"] == "Hoeffding"
        assert row["ci"][1] > rate
    else:
        assert row["interval_method"] == "Wilson"
        assert row["ci"] == pytest.approx([v * 100 for v in wilson_interval(wins, 200)])

    rendered = league_evolve.render_report({
        "board": "Test kingdom", "arm": "league", "rounds": 0,
        "worst_case_weight": .5, "capacity": 1, "final_league": [],
        "gate": [row], "round_reports": [],
    })
    assert f"| {wins} | {losses} | {ties} | {truncated} | {rate:.1f}% |" in rendered
    assert row["interval_method"] in rendered
