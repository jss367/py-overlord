"""Integration test: a Plunder Trait + new card combo runs a full short game."""

import random

from dominion.ai.base_ai import AI
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.traits import apply_trait


class _AI(AI):
    def __init__(self):
        self.strategy = None

    @property
    def name(self):
        return "ai"

    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_buy(self, state, choices):
        for prefer in ("Province", "Gold", "Sack of Loot", "Silver"):
            for c in choices:
                if c is not None and c.name == prefer:
                    return c
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is not None and c.name in ("Curse", "Estate", "Copper"):
                return c
        return None


def test_plunder_short_game_with_trait_runs():
    random.seed(123)
    kingdom = [get_card(n) for n in [
        "Cage", "Sack of Loot", "Mining Road", "Longship",
        "Pendant", "Frigate", "Cabin Boy", "Gondola",
        "Mapmaker", "Quartermaster",
    ]]
    state = GameState(players=[])
    state.initialize_game([_AI(), _AI()], kingdom)
    # Apply a trait to one of the kingdom piles.
    apply_trait(state, "Cheap", "Sack of Loot")
    # Should now cost $5 instead of $6.
    assert state.get_card_cost(state.current_player, get_card("Sack of Loot")) == 5
    # Run a few turns without crashing.
    for _ in range(80):
        if state.is_game_over():
            break
        state.play_turn()
    # Sanity: no exceptions, players still exist.
    assert all(p.get_victory_points() is not None for p in state.players)


def test_plunder_event_purchase_during_buy_phase():
    random.seed(1)
    state = GameState(players=[])
    state.initialize_game([_AI(), _AI()], [
        get_card(n) for n in [
            "Village", "Smithy", "Witch", "Festival", "Market",
            "Wharf", "Sack of Loot", "Mining Road", "Cabin Boy", "Gondola",
        ]
    ])
    state.events = [get_event("Bury"), get_event("Foray"), get_event("Launch")]
    # Run a few turns; ensure events can coexist.
    for _ in range(30):
        if state.is_game_over():
            break
        state.play_turn()
    # No crash.
