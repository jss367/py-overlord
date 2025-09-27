import types

from dominion.simulation.genetic_trainer import GeneticTrainer
from dominion.strategy.enhanced_strategy import PriorityRule
from dominion.strategy.strategies.base_strategy import BaseStrategy


def make_stub_strategy() -> BaseStrategy:
    strategy = BaseStrategy()
    strategy.name = "Stub"
    strategy.gain_priority = [PriorityRule("Province")]
    strategy.treasure_priority = [
        PriorityRule("Gold"),
        PriorityRule("Silver"),
        PriorityRule("Copper"),
    ]
    return strategy


def test_evaluate_strategy_counts_second_seat_wins(monkeypatch):
    trainer = GeneticTrainer(["Village"], population_size=1, generations=1, games_per_eval=2)

    # Provide a deterministic strategy under test
    strategy = make_stub_strategy()

    call_counter = types.SimpleNamespace(count=0)

    def fake_run_game(first_ai, second_ai, kingdom):
        call_counter.count += 1
        # Big Money (second_ai in the first call) wins when our strategy leads.
        # Our strategy (second_ai in the second call) wins when going second.
        return second_ai, {}, None, 0

    monkeypatch.setattr(trainer.battle_system, "run_game", fake_run_game)

    win_rate = trainer.evaluate_strategy(strategy)

    assert call_counter.count == 2
    assert win_rate == 50.0
