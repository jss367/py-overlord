"""Way of the Chameleon — Follow the card's instructions, swapping +Cards
and +$.
"""

from .base_way import Way


class WayOfTheChameleon(Way):
    def __init__(self):
        super().__init__("Way of the Chameleon")

    def apply(self, game_state, card) -> None:
        player = game_state.current_player
        # Apply baseline non-cards-non-coins effects from stats, then apply
        # the swap. The simplest accurate model: temporarily mutate the card
        # so that on_play sees swapped numbers, then restore.
        original_cards = card.stats.cards
        original_coins = card.stats.coins
        try:
            card.stats.cards = original_coins
            card.stats.coins = original_cards
            # Mark a flag so play_effect can skip cards-vs-coins-swappable
            # logic if a card opted in. Most cards rely solely on the base
            # CardStats accounting in Card.on_play, so swapping here is enough.
            card._chameleon_active = True
            card.on_play(game_state)
        finally:
            card.stats.cards = original_cards
            card.stats.coins = original_coins
            card._chameleon_active = False
