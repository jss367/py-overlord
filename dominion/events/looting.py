from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from .base_event import Event


class Looting(Event):
    """Event that gains a Gold when bought."""

    def __init__(self):
        super().__init__("Looting", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        gold = get_card("Gold")
        player.discard.append(gold)
        gold.on_gain(game_state, player)
