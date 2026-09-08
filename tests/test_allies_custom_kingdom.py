"""Automatic Ally discovery accepts custom Kingdom card objects."""

import pytest

from dominion.cards.base_card import Card, CardCost, CardStats, CardType
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.test_allies_printed_rules import ProbeAI


@pytest.mark.parametrize("custom_liaison", [False, True])
@pytest.mark.parametrize("wizards", [False, True])
def test_automatic_ally_discovery_accepts_unregistered_cards(custom_liaison, wizards):
    types = [CardType.ACTION]
    if custom_liaison:
        types.append(CardType.LIAISON)
    custom = Card("Custom Kingdom", CardCost(coins=3), CardStats(), types)
    kingdom = [custom] + ([get_card("Sorcerer")] if wizards else [])
    s = GameState(players=[])
    s.log_callback = lambda *args: None
    s.initialize_game([ProbeAI(), ProbeAI()], kingdom)
    assert s.supply[custom.name] == 10
    assert len(s.allies) == int(custom_liaison or wizards)
    assert all(p.favors == int(custom_liaison or wizards) for p in s.players)
