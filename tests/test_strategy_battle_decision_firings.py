from types import SimpleNamespace

from dominion.ai.genetic_ai import GeneticAI
from dominion.reporting.html_report import _decision_firings_section
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


def _card(name):
    return SimpleNamespace(name=name)


def test_choose_gain_matching_top_priority_is_not_counted_as_override():
    strategy = EnhancedStrategy()
    strategy.gain_priority = [PriorityRule("Gold"), PriorityRule("Silver")]
    ai = GeneticAI(strategy)
    battle = StrategyBattle()
    stats = battle._empty_decision_firings("Priority Strategy")
    state = SimpleNamespace(current_player=SimpleNamespace())

    battle._instrument_ai_decisions(ai, stats)

    selected = ai.choose_buy(state, [_card("Gold"), _card("Silver"), None])

    assert selected.name == "Gold"
    assert stats["choose_gain_overrides"]["total"] == 0
    assert stats["choose_gain_overrides"]["by_selection"] == {}


def test_choose_gain_bypassing_priority_and_choose_way_are_counted():
    class OverrideStrategy(EnhancedStrategy):
        def choose_gain(self, state, player, choices):
            return next(card for card in choices if card.name == "Smithy")

        def choose_way(self, state, player, card, ways):
            return next(way for way in ways if way is not None and way.name == "Way of the Butterfly")

    strategy = OverrideStrategy()
    strategy.gain_priority = [PriorityRule("Gold")]
    ai = GeneticAI(strategy)
    battle = StrategyBattle()
    stats = battle._empty_decision_firings("Override Strategy")
    state = SimpleNamespace(current_player=SimpleNamespace())

    battle._instrument_ai_decisions(ai, stats)

    selected = ai.choose_buy(state, [_card("Gold"), _card("Smithy"), None])
    way = ai.choose_way(state, _card("Flag Bearer"), [_card("Way of the Butterfly"), None])

    assert selected.name == "Smithy"
    assert way.name == "Way of the Butterfly"
    assert stats["choose_gain_overrides"]["total"] == 1
    assert stats["choose_gain_overrides"]["by_selection"] == {"Smithy over Gold": 1}
    assert stats["choose_way"] == {"Flag Bearer": {"Way of the Butterfly": 1}}


def test_html_decision_firings_section_renders_zero_rows():
    results = {
        "decision_firings": {
            "strategy1": StrategyBattle._empty_decision_firings("No Overrides"),
            "strategy2": StrategyBattle._empty_decision_firings("Also Quiet"),
        }
    }

    section = _decision_firings_section(results)

    assert "Decision Firings" in section
    assert "No Overrides" in section
    assert "No non-default Way choices or gain special cases" in section
    assert "<td>0</td>" in section
