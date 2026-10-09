"""Supply gain accounting stays consistent through replacements and reactions."""

from collections import Counter
import random

import pytest

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


class GainAI(DummyAI):
    reveal_trader = False
    watchtower = None
    changeling = False

    def should_reveal_trader(self, state, player, card, *, to_deck):
        return self.reveal_trader

    def choose_watchtower_reaction(self, state, player, card):
        return self.watchtower

    def should_exchange_changeling(self, state, player, card):
        return self.changeling


def make_state(supply=None):
    player = PlayerState(GainAI())
    state = GameState([player], supply=dict(supply or {"Village": 2, "Silver": 4}))
    state.log_callback = lambda *_: None
    return state, player


def inventory(state):
    """Count physical cards in these fixtures, excluding Duration bookkeeping."""
    counts = Counter(
        {name: n for name, n in state.supply.items() if name not in state.pile_order}
    )
    for names in state.pile_order.values():
        counts.update(names)
    owned = [
        card
        for player in state.players
        for zone in player._physical_card_zones()
        for card in zone
    ]
    cards = owned + state.trash
    assert len({id(card) for card in cards}) == len(cards), (
        "card occupies multiple physical zones"
    )
    counts.update(card.name for card in cards)
    assert all(n >= 0 for n in state.supply.values())
    for pile, names in state.pile_order.items():
        assert state.supply[pile] == len(names)
    return +counts


@pytest.mark.parametrize(
    "destination,zone", [("discard", "discard"), ("deck", "deck"), ("hand", "hand")]
)
def test_gain_decrements_once_and_returns_card_at_requested_destination(
    destination, zone
):
    state, player = make_state()
    before = inventory(state)
    state.phase = "buy"
    gained = state.gain_from_supply(player, "Village", destination=destination)
    assert gained is getattr(player, zone)[-1]
    assert state.supply["Village"] == 1
    assert player.cards_gained_this_turn == player.cards_gained_this_buy_phase == 1
    assert player.gained_cards_this_turn == ["Village"]
    assert inventory(state) == before


def test_repeated_gain_stops_at_empty_pile():
    state, player = make_state({"Village": 1})
    before = inventory(state)
    assert state.gain_from_supply(player, "Village") is not None
    for _ in range(3):
        assert state.gain_from_supply(player, "Village") is None
    assert player.cards_gained_this_turn == 1
    assert inventory(state) == before


@pytest.mark.parametrize(
    "case", ["absent", "empty", "covered", "non_supply", "reserved"]
)
def test_unavailable_target_does_not_mutate_supply_or_gain_history(case):
    state, player = make_state({"Catapult": 1, "Rocks": 1, "Horse": 3})
    target = {
        "absent": "Village",
        "empty": "Catapult",
        "covered": "Rocks",
        "non_supply": "Horse",
        "reserved": "Catapult",
    }[case]
    if case == "empty":
        state.supply["Catapult"] = 0
    elif case == "non_supply":
        state.non_supply_pile_names.add("Horse")
    elif case == "reserved":
        state.ferryman_card_name = "Catapult"
    before = inventory(state)
    supply = dict(state.supply)
    assert state.gain_from_supply(player, target) is None
    assert state.supply == supply
    assert player.cards_gained_this_turn == 0
    assert player.gained_cards_this_turn == []
    assert inventory(state) == before


def test_invalid_destination_fails_before_removal():
    state, player = make_state()
    before = inventory(state)
    with pytest.raises(ValueError, match="destination"):
        state.gain_from_supply(player, "Village", destination="somewhere")
    assert state.supply["Village"] == 2 and player.cards_gained_this_turn == 0
    assert inventory(state) == before


@pytest.mark.parametrize("destination", ["discard", "deck", "hand"])
@pytest.mark.parametrize("reaction", ["topdeck", "trash"])
def test_watchtower_can_redirect_or_trash_each_destination(destination, reaction):
    state, player = make_state()
    player.hand = [get_card("Watchtower")]
    player.ai.watchtower = reaction
    before = inventory(state)
    gained = state.gain_from_supply(player, "Village", destination=destination)
    assert gained in (player.deck if reaction == "topdeck" else state.trash)
    assert state.supply["Village"] == 1
    assert player.cards_gained_this_turn == 1
    assert inventory(state) == before


@pytest.mark.parametrize(
    "pile,name",
    [
        ("Village", "Village"),
        ("Catapult", "Catapult"),
        ("Knights", "Sir Martin"),
        ("Ruins", "Abandoned Mine"),
    ],
)
def test_trader_restores_exact_pile_and_only_consumes_silver(pile, name):
    state, player = make_state({pile: 1, "Silver": 2})
    if pile in {"Knights", "Ruins"}:
        state.pile_order[pile] = [name]
    elif pile == "Catapult":
        state.supply["Rocks"] = 2
    player.hand = [get_card("Trader")]
    player.ai.reveal_trader = True
    before = inventory(state)
    gained = state.gain_from_supply(player, name, destination="hand")
    assert gained.name == "Silver" and gained in player.hand
    assert state.supply[pile] == 1 and state.supply["Silver"] == 1
    assert state.top_supply_card(pile) == name
    assert player.gained_cards_this_turn == ["Silver"]
    assert inventory(state) == before


def test_trader_without_silver_keeps_original_gain():
    state, player = make_state({"Village": 1, "Silver": 0})
    player.hand = [get_card("Trader")]
    player.ai.reveal_trader = True
    before = inventory(state)
    assert state.gain_from_supply(player, "Village").name == "Village"
    assert state.supply["Village"] == 0 and state.supply["Silver"] == 0
    assert inventory(state) == before


def test_split_pile_transition_does_not_substitute_a_newly_exposed_card():
    state, player = make_state({"Catapult": 1, "Rocks": 2, "Silver": 2})
    before = inventory(state)
    assert state.gain_from_supply(player, "Catapult").name == "Catapult"
    assert state.top_supply_card("Catapult") == "Rocks"
    assert state.gain_from_supply(player, "Catapult") is None
    assert state.gain_from_supply(player, "Rocks").name == "Rocks"
    # Rocks' own gain effect also gains one Silver.
    assert state.supply["Rocks"] == 1 and state.supply["Silver"] == 1
    assert inventory(state) == before


def test_changeling_exchange_returns_original_and_preserves_location():
    state, player = make_state({"Village": 1, "Changeling": 1})
    player.ai.changeling = True
    before = inventory(state)
    gained = state.gain_from_supply(player, "Village", destination="deck")
    assert gained.name == "Changeling" and gained is player.deck[-1]
    assert state.supply == {"Village": 1, "Changeling": 0}
    assert inventory(state) == before


def test_nested_gain_sees_last_copy_removed_before_reactions(monkeypatch):
    state, player = make_state({"Village": 1})
    original = get_card("Village").__class__.on_gain
    nested = []

    def on_gain(card, game, owner):
        original(card, game, owner)
        nested.append(game.gain_from_supply(owner, "Village"))

    monkeypatch.setattr(get_card("Village").__class__, "on_gain", on_gain)
    before = inventory(state)
    state.gain_from_supply(player, "Village")
    assert nested == [None]
    assert player.cards_gained_this_turn == 1
    assert inventory(state) == before


@pytest.mark.parametrize("seed", [17, 101, 1729, 4242])
def test_seeded_gain_sequences_conserve_cards_and_never_duplicate_locations(seed):
    rng = random.Random(seed)
    state, player = make_state(
        {"Village": 5, "Silver": 12, "Gold": 4, "Catapult": 2, "Rocks": 2, "Knights": 2}
    )
    state.pile_order["Knights"] = ["Dame Anna", "Sir Martin"]
    player.hand = [get_card("Trader"), get_card("Watchtower")]
    before = inventory(state)
    names = [
        "Village",
        "Silver",
        "Gold",
        "Catapult",
        "Rocks",
        "Sir Martin",
        "Dame Anna",
    ]
    for _ in range(100):
        player.ai.reveal_trader = rng.choice([False, True])
        player.ai.watchtower = rng.choice([None, "topdeck", "trash"])
        state.gain_from_supply(
            player,
            rng.choice(names),
            destination=rng.choice(["discard", "deck", "hand"]),
        )
        assert inventory(state) == before


def test_named_split_member_can_be_gained_without_an_empty_partner_key():
    state, player = make_state({"Rocks": 1, "Silver": 1})
    before = inventory(state)
    assert state.gain_from_supply(player, "Rocks").name == "Rocks"
    assert state.supply == {"Rocks": 0, "Silver": 0}
    assert inventory(state) == before


def test_artificer_cannot_gain_a_different_card_exposed_by_discard_reactions(
    monkeypatch,
):
    state, player = make_state({"Catapult": 1, "Rocks": 2})
    player.hand = [get_card("Copper") for _ in range(3)]
    player.ai.choose_artificer_gain = lambda state, player, choices: next(
        c for c in choices if c.name == "Catapult"
    )
    discard = state.discard_card

    def discard_and_gain(owner, card, **kwargs):
        discard(owner, card, **kwargs)
        # Model a nested gain caused by a discard reaction consuming the last
        # Catapult after Artificer has already selected it from the old menu.
        state.gain_from_supply(owner, "Catapult")

    monkeypatch.setattr(state, "discard_card", discard_and_gain)
    before = inventory(state)
    get_card("Artificer").play_effect(state)
    assert state.top_supply_card("Catapult") == "Rocks"
    assert state.supply["Rocks"] == 2 and player.deck == []
    assert player.gained_cards_this_turn == ["Catapult"]
    assert inventory(state) == before


@pytest.mark.parametrize("seed_rng", [17, 101, 1729], indirect=True)
def test_seeded_games_with_migrated_gainers_conserve_cards_each_phase(
    seed_rng, monkeypatch
):
    from dominion.ai.genetic_ai import GeneticAI
    from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule

    kingdom = [
        "Workshop",
        "Remodel",
        "Anvil",
        "Quartermaster",
        "Armory",
        "Artificer",
        "Village",
        "Smithy",
        "Market",
        "Chapel",
    ]
    strategies = []
    for _ in range(2):
        strategy = EnhancedStrategy()
        strategy.gain_priority = (
            [PriorityRule("Province")]
            + [
                PriorityRule(name, PriorityRule.max_in_deck(name, 1))
                for name in kingdom[:6]
            ]
            + [PriorityRule("Gold"), PriorityRule("Silver")]
        )
        strategy.free_gain_priority = [
            PriorityRule("Village", PriorityRule.max_in_deck("Village", 3)),
            PriorityRule("Smithy", PriorityRule.max_in_deck("Smithy", 2)),
            PriorityRule("Silver"),
        ]
        strategy.action_priority = [
            PriorityRule(name) for name in ["Village"] + kingdom[:6] + ["Smithy"]
        ]
        strategy.trash_priority = [PriorityRule("Estate")]
        strategies.append(strategy)
    state = GameState([])
    state.log_callback = lambda *_: None
    state.initialize_game(
        [GeneticAI(s) for s in strategies], [get_card(n) for n in kingdom]
    )
    before = inventory(state)
    committed = []
    gain = GameState.gain_from_supply

    def checked_gain(game, player, name, **kwargs):
        result = gain(game, player, name, **kwargs)
        if game is state and result is not None:
            committed.append(result)
        return result

    monkeypatch.setattr(GameState, "gain_from_supply", checked_gain)
    # play_turn advances a single phase; allow enough steps for the turn cap.
    for _ in range(3000):
        if state.is_game_over():
            break
        state.play_turn()
        assert inventory(state) == before
    assert state.is_game_over()
    assert committed, "the game must exercise the migrated gain operation"
