"""Regression tests for Lurker and Lich trash-gain paths.

Both cards can pull a card out of the trash and put it into the player's
deck/discard. These paths must route through ``GameState.gain_card`` so the
gain participates in shared bookkeeping (``cards_gained_this_turn``,
``actions_gained_this_turn``, project on-gain hooks, Watchtower/Insignia/
Royal Seal reactions, and the Cauldron third-Action-gain curse trigger).
"""

from dominion.cards.allies.wizards import Lich
from dominion.cards.intrigue.lurker import Lurker
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _GainFromTrashAI:
    """AI that picks Lurker mode='gain' and trashes/gains a fixed card."""

    def __init__(self, target_name: str | None = None):
        self.name = "trash-gain"
        self.target_name = target_name
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, state, choices):
        return choices[0] if choices else None

    def choose_lurker_mode(self, state, player, can_trash, can_gain):
        return "gain" if can_gain else "trash"

    def choose_action_to_gain_from_trash(self, state, player, choices):
        if self.target_name:
            for c in choices:
                if c.name == self.target_name:
                    return c
        return choices[0] if choices else None

    def choose_card_to_gain_from_trash(self, state, player, choices, max_cost):
        if self.target_name:
            for c in choices:
                if c.name == self.target_name:
                    return c
        return choices[0] if choices else None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        # Drop the cheapest cards.
        ordered = sorted(choices, key=lambda c: (c.cost.coins, c.name))
        return ordered[:count]


def _setup(kingdom_extras: list[str] = ()) -> tuple[GameState, PlayerState]:
    state = GameState(players=[])
    state.players = [PlayerState(_GainFromTrashAI())]
    cards = [get_card("Village")] + [get_card(n) for n in kingdom_extras]
    state.setup_supply(cards)
    return state, state.players[0]


def test_lurker_trash_gain_increments_cards_gained_this_turn():
    state, player = _setup()
    village = get_card("Village")
    state.trash.append(village)

    before = player.cards_gained_this_turn
    Lurker().play_effect(state)

    assert player.cards_gained_this_turn == before + 1, (
        "Lurker's trash gain should bump cards_gained_this_turn so it "
        "participates in the same bookkeeping as buy-phase gains"
    )
    assert village in player.discard, "Gained card should land in discard"
    assert village not in state.trash, "Gained card should leave the trash"


def test_lurker_trash_gain_increments_actions_gained_this_turn():
    """Cauldron-style trigger: action gains from trash must count."""
    state, player = _setup()
    village = get_card("Village")
    state.trash.append(village)

    before = player.actions_gained_this_turn
    Lurker().play_effect(state)

    assert player.actions_gained_this_turn == before + 1, (
        "Lurker's trash gain should advance actions_gained_this_turn so "
        "Cauldron's third-Action-gain trigger fires consistently"
    )


def test_lich_trash_gain_increments_cards_gained_this_turn():
    """Lich's '+ gain a cheaper Action from trash' clause must also route through gain_card."""
    state, player = _setup()
    # Put a cheaper Action in trash (Village costs $3, less than Lich's $6).
    village = get_card("Village")
    state.trash.append(village)
    # Lich draws +6 / +2A then asks the AI to discard 2 — give the player a hand.
    player.hand = [get_card("Copper") for _ in range(3)]

    before_cards = player.cards_gained_this_turn
    before_actions = player.actions_gained_this_turn
    Lich().play_effect(state)

    assert player.cards_gained_this_turn == before_cards + 1
    assert player.actions_gained_this_turn == before_actions + 1
    assert village in player.discard
    assert village not in state.trash
