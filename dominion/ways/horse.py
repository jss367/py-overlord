"""Way of the Horse — +2 Cards +1 Action. Return this to its pile."""

from .base_way import Way


class WayOfTheHorse(Way):
    def __init__(self):
        super().__init__("Way of the Horse")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        # Return the played card to its supply pile. Only do so if the card
        # actually has a pile in the supply — otherwise we'd manufacture a
        # synthetic pile for cards that were never in the Supply (e.g. cards
        # gained from non-Supply piles or set-aside zones).
        if card in player.in_play and card.name in game_state.supply:
            player.in_play.remove(card)
            game_state.supply[card.name] += 1
