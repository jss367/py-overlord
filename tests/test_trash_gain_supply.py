"""Trader returns trash-origin gains to their piles instead of losing them.

The caller removes a physical card from trash without taking another Supply
copy. Returning that card through Trader increases its pile by one.
"""

from dominion.cards.allies.wizards import Lich
from dominion.cards.intrigue.lurker import Lurker
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _RevealsTraderAI:
    name = "trader-reveal"

    def __init__(self):
        self.strategy = None

    def choose_action(self, *a, **k):
        return None

    def choose_treasure(self, *a, **k):
        return None

    def choose_buy(self, *a, **k):
        return None

    def choose_card_to_trash(self, state, choices):
        return choices[0] if choices else None

    def choose_lurker_mode(self, state, player, can_trash, can_gain):
        return "gain" if can_gain else "trash"

    def choose_action_to_gain_from_trash(self, state, player, choices):
        return choices[0] if choices else None

    def choose_card_to_gain_from_trash(self, state, player, choices, max_cost):
        return choices[0] if choices else None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        # Preserve Trader so it can react to the gain.
        ranked = sorted(choices, key=lambda c: 0 if c.name != "Trader" else 1)
        return ranked[:count]

    def should_reveal_trader(self, state, player, gained_card, *, to_deck):
        # Always reveal Trader so the exchange flow runs.
        return True


def _setup() -> tuple[GameState, PlayerState]:
    state = GameState(players=[])
    state.players = [PlayerState(_RevealsTraderAI())]
    state.setup_supply([get_card("Village")])
    return state, state.players[0]


def test_lurker_trash_gain_with_trader_returns_the_card_to_its_pile():
    state, player = _setup()
    state.trash.append(state.take_top_supply_card("Village"))
    village_supply_before = state.supply["Village"]
    silver_supply_before = state.supply["Silver"]

    # Set up: Village in trash for Lurker to gain; Trader in hand.
    player.hand = [get_card("Trader")]

    Lurker().play_effect(state)

    # Trader replaced the gain with Silver. Pile-count invariants:
    #   - Village returns to Supply (it came from trash).
    #   - Silver supply went down by exactly 1.
    assert state.supply["Village"] == village_supply_before + 1, (
        f"Village supply should increase by the returned copy; before={village_supply_before}, after={state.supply['Village']}"
    )
    assert state.supply["Silver"] == silver_supply_before - 1, (
        f"Silver supply should decrement by 1; before={silver_supply_before}, after={state.supply['Silver']}"
    )
    assert any(c.name == "Silver" for c in player.discard), (
        "Player should end up with Silver"
    )


def test_lich_trash_gain_with_trader_returns_the_card_to_its_pile():
    state, player = _setup()
    state.trash.append(state.take_top_supply_card("Village"))
    village_supply_before = state.supply["Village"]
    silver_supply_before = state.supply["Silver"]

    player.hand = [get_card("Trader"), get_card("Copper"), get_card("Copper")]

    state.trash_card(player, Lich())

    assert state.supply["Village"] == village_supply_before + 1, (
        f"Village supply should increase by the returned copy; before={village_supply_before}, after={state.supply['Village']}"
    )
    assert state.supply["Silver"] == silver_supply_before - 1
    assert any(c.name == "Silver" for c in player.discard)
