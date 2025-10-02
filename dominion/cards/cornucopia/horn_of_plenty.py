from ..base_card import Card, CardCost, CardStats, CardType


class HornOfPlenty(Card):
    """Treasure that rewards diverse action play."""

    def __init__(self):
        super().__init__(
            name="Horn of Plenty",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        unique_cards = {card.name for card in player.in_play}
        player.coins += len(unique_cards)
