import random
from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from dominion.cards.plunder import LOOT_CARD_NAMES
from .base_event import Event


class Looting(Event):
    """Event that gains a random Loot when bought."""

    def __init__(self):
        super().__init__("Looting", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        loot_name = random.choice(LOOT_CARD_NAMES)
        loot = get_card(loot_name)
        game_state.gain_card(player, loot)
