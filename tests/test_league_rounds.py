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
