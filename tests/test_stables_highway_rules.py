"""Physical rule scenarios required before interpreting this board's search."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.strategy.strategies.stables_highway import StablesHighway
from tests.utils import DummyAI


class PickAI(DummyAI):
    def __init__(self, name):
        self.target = name
        self.menus = []

    def choose_free_gain(self, state, player, choices, context):
        self.menus.append((context.source, [c.name for c in choices]))
        return next((c for c in choices if c.name == self.target), None)

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return sorted(choices, key=lambda c: c.name != "Weaver")[:count]


def test_weaver_can_gain_discounted_five_cost_action():
    ai = PickAI("Stables")
    player = PlayerState(ai)
    state = GameState([player], supply={"Stables": 10, "Silver": 40})
    player.cost_reduction = 1
    get_card("Weaver").play_effect(state)
    assert [c.name for c in player.discard] == ["Stables"]
    assert state.supply["Stables"] == 9


def test_weaver_two_silvers_is_separate_from_one_silver():
    for target, expected in [("Silver", 1), (None, 2)]:
        player = PlayerState(PickAI(target))
        state = GameState([player], supply={"Silver": 40})
        get_card("Weaver").play_effect(state)
        assert len(player.discard) == expected


def test_develop_uses_discounted_cost_of_trashed_copper():
    player = PlayerState(PickAI("Estate"))
    state = GameState([player], supply={"Copper": 40, "Estate": 8, "Silver": 40})
    player.cost_reduction = 1
    copper = get_card("Copper")
    player.hand = [copper]
    get_card("Develop").play_effect(state)
    assert copper in state.trash
    assert [c.name for c in player.deck] == ["Estate"]


def test_haggler_cannot_gain_a_card_with_equal_zero_cost():
    ai = PickAI("Silver")
    player = PlayerState(ai)
    state = GameState([player], supply={"Copper": 40, "Silver": 40, "Guard Dog": 10})
    player.cost_reduction = 4
    player.in_play = [get_card("Haggler")]
    state._trigger_haggler_bonus(player, get_card("Guard Dog"))
    assert player.discard == []
    assert ai.menus == []


def test_haggler_mandatory_gain_does_not_stop_when_ai_declines():
    player = PlayerState(DummyAI())
    state = GameState([player], supply={"Copper": 40})
    player.in_play = [get_card("Haggler")]
    state._trigger_haggler_bonus(player, get_card("Gold"))
    assert [c.name for c in player.discard] == ["Copper"]


def test_witchs_hut_can_discard_two_actions_and_curse():
    player = PlayerState(GeneticAI(StablesHighway()))
    other = PlayerState(DummyAI())
    state = GameState([player, other], supply={"Curse": 10})
    player.hand = [get_card("Develop"), get_card("Guard Dog"), get_card("Estate")]
    get_card("Witch's Hut").play_effect(state)
    assert {c.name for c in player.discard} == {"Develop", "Guard Dog"}
    assert [c.name for c in other.discard] == ["Curse"]


def test_margrave_discards_weaver_with_defenders_policy():
    player = PlayerState(DummyAI())
    ai = PickAI("Silver")
    target = PlayerState(ai)
    state = GameState([player, target], supply={"Silver": 40})
    target.hand = [get_card("Weaver"), get_card("Gold"), get_card("Gold"), get_card("Gold")]
    get_card("Margrave").play_effect(state)
    assert len(target.hand) == 3
    assert [c.name for c in target.in_play] == ["Weaver"]
    assert [c.name for c in target.discard] == ["Silver"]
    assert ai.menus[0][0] == "Weaver"


def test_simultaneous_discards_are_in_discard_before_weaver_reacts():
    class ObserveAI(PickAI):
        def should_play_weaver_on_discard(self, state, player, card):
            assert len(player.hand) == 0
            assert {c.name for c in player.discard} == {"Weaver", "Estate"}
            return False
    player = PlayerState(ObserveAI("Silver"))
    state = GameState([player], supply={"Silver": 40})
    player.hand = [get_card("Weaver"), get_card("Estate")]
    get_card("Inn").play_effect(state)


def test_guard_dog_reacts_even_when_witchs_hut_does_not_curse():
    player = PlayerState(DummyAI())
    other = PlayerState(DummyAI())
    state = GameState([player, other], supply={"Curse": 10})
    player.hand = [get_card("Estate"), get_card("Copper")]
    other.hand = [get_card("Guard Dog")]
    other.deck = [get_card("Gold") for _ in range(4)]
    get_card("Witch's Hut").play_effect(state)
    assert [c.name for c in other.in_play] == ["Guard Dog"]
    assert len(other.hand) == 4
    assert state.supply["Curse"] == 10


def test_first_weaver_can_shuffle_second_weaver_away_before_its_reaction():
    player = PlayerState(PickAI("Inn"))
    state = GameState([player], supply={"Inn": 10, "Silver": 40})
    player.cost_reduction = 1
    first, second = get_card("Weaver"), get_card("Weaver")
    player.hand = [first, second]
    get_card("Inn").play_effect(state)
    assert player.in_play == [first]
    assert second in player.deck
    assert any(c.name == "Inn" for c in player.deck)
    assert state.supply["Inn"] == 9


def test_published_strategy_matches_frozen_validation_selection():
    import json
    from pathlib import Path
    from dominion.strategy.strategies.stables_highway import create_stables_highway_best_found

    config = json.loads(Path("scripts/data/stables_highway_selection.json").read_text())
    published = create_stables_highway_best_found()
    assert published.params == StablesHighway(**config["winner"]).params
    assert {r.card for r in published.action_priority} == {"Margrave"}
