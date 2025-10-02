from ..base_card import Card, CardCost, CardStats, CardType


class Menagerie(Card):
    """Draws extra cards when the player's hand has unique names."""

    def __init__(self):
        super().__init__(
            name="Menagerie",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        hand_names = [card.name for card in player.hand]
        has_duplicates = len(hand_names) != len(set(hand_names))
        draw_count = 3 if not has_duplicates else 1
        if draw_count:
            game_state.draw_cards(player, draw_count)
