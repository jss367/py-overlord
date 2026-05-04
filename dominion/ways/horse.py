"""Way of the Horse — +2 Cards +1 Action. Return this to its pile."""

from .base_way import Way


class WayOfTheHorse(Way):
    def __init__(self):
        super().__init__("Way of the Horse")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        # Return the played card to its supply pile
        if card in player.in_play:
            player.in_play.remove(card)
            game_state.supply[card.name] = game_state.supply.get(card.name, 0) + 1
