"""Rules that materially affect this kingdom's strategy comparisons."""

from dominion.ai.genetic_ai import GeneticAI
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.strategy.strategies.collection_imperial_envoy import (
    CollectionImperialEnvoy,
)
from tests.utils import DummyAI


def setup(top):
    state = GameState(players=[], supply={})
    state.initialize_game(
        [GeneticAI(CollectionImperialEnvoy()), DummyAI()],
        [get_card(n) for n in ("Tent", "Swindler", "Sleigh", "Collection")],
    )
    state.log_callback = lambda *_: None
    target = state.players[1]
    target.hand = []
    target.deck = [get_card(top)]
    target.discard = []
    return state, target


def test_swindler_gives_curse_instead_of_attackers_purchase_choice():
    state, target = setup("Copper")
    before = state.supply["Curse"]
    get_card("Swindler").play_effect(state)
    assert [c.name for c in target.discard] == ["Curse"]
    assert state.supply["Curse"] == before - 1
    assert state.trash[-1].name == "Copper"


def test_swindler_only_exposed_fort_and_updates_physical_pile():
    state, target = setup("Silver")
    before = state.supply["Tent"]
    get_card("Swindler").play_effect(state)
    assert [c.name for c in target.discard] == ["Tent"]
    assert state.supply["Tent"] == before - 1
    from dominion.game.supply_piles import stack

    assert stack(state, "Tent").count("Tent") == before - 1
    state.rotate_supply_pile("Tent")
    target.deck = [get_card("Silver")]
    target.discard = []
    get_card("Swindler").play_effect(state)
    assert [c.name for c in target.discard] == ["Silver"]


def test_swindler_excludes_horses_and_matches_debt_cost():
    state, target = setup("Estate")
    seen = []

    def choose(state, player, target, choices):
        seen.extend(c.name for c in choices)
        return choices[0]

    state.players[0].ai.choose_swindler_replacement = choose
    get_card("Swindler").play_effect(state)
    assert "Horse" not in seen
    assert "Sleigh" in seen
    state, target = setup("City Quarter")
    get_card("Swindler").play_effect(state)
    assert not target.discard  # No exposed card with the same 8-debt cost.


def test_collection_stacks_for_action_gains_but_not_ghost_town():
    state, player = setup("Copper")
    player.collection_played = 3
    state.gain_card(player, get_card("Village"))
    assert player.vp_tokens == 3
    state.gain_card(player, get_card("Ghost Town"))
    assert player.vp_tokens == 3


def test_mystic_naming_is_order_independent_and_can_name_copper():
    state, player = setup("Copper")
    player.deck = [get_card(n) for n in ("Copper", "Silver", "Copper")]
    strategy = CollectionImperialEnvoy()
    assert strategy.name_card_for_mystic(state, player) == "Copper"
    player.deck.reverse()
    assert strategy.name_card_for_mystic(state, player) == "Copper"


def test_engine_does_not_take_envoy_debt_with_empty_draw_piles():
    from dominion.strategy.strategies.village_envoy_engine import VillageEnvoyEngine

    state, player = setup("Copper")
    player.deck = []
    player.discard = []
    player.hand = [get_card("Imperial Envoy")]
    policy = VillageEnvoyEngine()
    assert policy.choose_action(state, player, player.hand + [None]) is None
    player.deck = [get_card("Copper") for _ in range(5)]
    assert (
        policy.choose_action(state, player, player.hand + [None]).name
        == "Imperial Envoy"
    )


def test_engine_preserves_last_action_for_envoy_to_find_villages():
    from dominion.strategy.strategies.village_envoy_engine import VillageEnvoyEngine

    state, player = setup("Copper")
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [get_card("Swindler"), get_card("Imperial Envoy")]
    policy = VillageEnvoyEngine(attack_first=True)
    player.actions = 1
    assert policy.choose_action(state, player, player.hand).name == "Imperial Envoy"
    player.actions = 2
    assert policy.choose_action(state, player, player.hand).name == "Swindler"


def test_engine_uses_five_two_opening_for_draw():
    from dominion.strategy.strategies.village_envoy_engine import VillageEnvoyEngine

    state, player = setup("Copper")
    player.turns_taken = 1
    choices = [
        get_card(n) for n in ("Swindler", "Collection", "Imperial Envoy", "Silver")
    ]
    policy = VillageEnvoyEngine(first_five="Imperial Envoy")
    assert policy.choose_gain(state, player, choices).name == "Imperial Envoy"
