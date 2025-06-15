from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from .base_event import Event


class GainSilver(Event):
    """Simple example event that gains a Silver when bought."""

    def __init__(self):
        super().__init__("Gain Silver", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        silver = get_card("Silver")
        game_state.gain_card(player, silver)
