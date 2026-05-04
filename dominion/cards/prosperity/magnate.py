from ..base_card import Card, CardCost, CardStats, CardType


class Magnate(Card):
    """Action ($5): Reveal your hand. +1 Card per Treasure revealed."""

    def __init__(self):
        super().__init__(
            name="Magnate",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures_revealed = sum(1 for card in player.hand if card.is_treasure)
        if treasures_revealed:
            game_state.draw_cards(player, treasures_revealed)
