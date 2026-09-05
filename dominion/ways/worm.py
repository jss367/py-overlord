"""Way of the Worm — Exile this card. Gain an Estate."""

from dominion.cards.registry import get_card
from .base_way import Way


class WayOfTheWorm(Way):
    def __init__(self):
        super().__init__("Way of the Worm")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        # "Exile this card. Gain an Estate." The Exile only happens when the
        # card is in play (virtual plays and already-moved Throne Room
        # replays stay put); the Estate gain has no "if you did" and always
        # happens.
        if card in player.in_play:
            player.in_play.remove(card)
            player.exile.append(card)
        if game_state.supply.get("Estate", 0) > 0:
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))
