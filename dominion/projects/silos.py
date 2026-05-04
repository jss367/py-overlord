"""Silos: at the start of your turn, discard any number of Coppers, then
draw that many cards."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Silos(Project):
    def __init__(self) -> None:
        super().__init__("Silos", CardCost(coins=4))

    def on_turn_start(self, game_state, player) -> None:
        coppers = [c for c in player.hand if c.name == "Copper"]
        if not coppers:
            return
        for copper in coppers:
            player.hand.remove(copper)
            game_state.discard_card(player, copper)
        game_state.draw_cards(player, len(coppers))
