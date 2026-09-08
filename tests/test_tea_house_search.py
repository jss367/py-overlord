"""Check that search diagnostics distinguish normal endings from turn caps."""

import pytest

from scripts import search_tea_house_kind_emperor as search
from dominion.game.player_state import PlayerState
from generated_strategies.tea_house_kind_emperor import create_tea_house_kind_emperor


def test_published_strategy_buys_gold_before_tea_house_pile_is_empty():
    strategy = create_tea_house_kind_emperor()
    player = PlayerState(ai=search.GeneticAI(strategy), turns_taken=6, coins=6)
    player.deck = [
        search.get_card(name)
        for name in ["Tea House"] * 4 + ["Silver"] * 2 + ["Fortune Hunter"]
    ]
    state = search.GameState(
        players=[player], supply={"Province": 8, "Tea House": 6, "Gold": 30},
        phase="buy",
    )
    choices = [search.get_card(name) for name in ["Tea House", "Gold", "Silver"]]

    assert player.ai.choose_buy(state, choices).name == "Gold"
    player.deck.extend(search.get_card("Gold") for _ in range(2))
    assert player.ai.choose_buy(state, choices) is None
    assert state.supply["Tea House"] == 6


@pytest.mark.parametrize("turn_limit", [101, 160])
@pytest.mark.parametrize("normal_end", [False, True])
def test_search_reports_only_unnatural_turn_limit_endings_as_truncated(
    monkeypatch, turn_limit, normal_end
):
    class EndAtLimit(search.GameState):
        def play_turn(self):
            self.turn_number = turn_limit
            if normal_end:
                self.supply["Province"] = 0

    monkeypatch.setattr(search, "GameState", EndAtLimit)

    result = search.match((search.CHAMPION, search.CHAMPION, 2, 100))

    assert result["truncated"] == (0 if normal_end else 2)
