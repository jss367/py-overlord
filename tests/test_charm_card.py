from __future__ import annotations

from typing import Optional

from dominion.cards.base_card import Card
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI


def make_state(ai: DummyAI) -> tuple[GameState, PlayerState]:
    player = PlayerState(ai)
    state = GameState(players=[player])
    state.log_callback = lambda *args, **kwargs: None
    return state, player


class CharmCoinsAI(DummyAI):
    def choose_charm_option(self, state: GameState, player: PlayerState, options: list[str]) -> str:
        return "coins"


def test_charm_coin_option_adds_two_coins():
    state, player = make_state(CharmCoinsAI())
    charm = get_card("Charm")

    player.coins = 0

    charm.play_effect(state)

    assert player.coins == 2


class CharmGainAI(DummyAI):
    def choose_charm_option(self, state: GameState, player: PlayerState, options: list[str]) -> str:
        return "gain"

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]):
        for choice in choices:
            if choice is not None:
                return choice
        return None


def test_charm_gain_option_only_allows_non_victory_cards():
    state, player = make_state(CharmGainAI())
    charm = get_card("Charm")

    state.supply = {"Silver": 5, "Estate": 5}

    charm.play_effect(state)

    assert state.supply["Silver"] == 4
    assert state.supply["Estate"] == 5
    assert any(card.name == "Silver" for card in player.discard)


class CharmCopyAI(DummyAI):
    def __init__(self):
        super().__init__()
        self._buy_used = False

    def choose_charm_option(self, state: GameState, player: PlayerState, options: list[str]) -> str:
        return "copy_next_buy"

    def choose_buy(self, state: GameState, choices: list[Optional[Card]]):
        if not self._buy_used:
            for choice in choices:
                if choice is not None and getattr(choice, "is_event", False) is False:
                    if choice.name == "Silver":
                        self._buy_used = True
                        return choice
        return None


def test_charm_copy_option_duplicates_next_purchase():
    state, player = make_state(CharmCopyAI())
    charm = get_card("Charm")

    state.supply = {"Silver": 5}
    player.coins = 3
    player.buys = 1

    charm.play_effect(state)

    state.handle_buy_phase()

    assert player.charm_next_buy_copies == 0
    assert state.supply["Silver"] == 3
    gained_silvers = [card for card in player.discard if card.name == "Silver"]
    assert len(gained_silvers) == 2
