"""Implementation of the Aristocrat card from Rising Sun."""

from ..base_card import Card, CardCost, CardStats, CardType


class Aristocrat(Card):
    """Aristocrat - Action ($5)

    Look at how many Aristocrats you have in play (counting this).
    If it's:
      1 or 5: +3 Actions
      2 or 6: +3 Cards
      3 or 7: +$3
      4 or 8: +3 Buys
    """

    def __init__(self):
        super().__init__(
            name="Aristocrat",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Count Aristocrats in play (this card is already in play when play_effect runs)
        count = sum(1 for card in player.in_play if card.name == "Aristocrat")

        # Effect cycles based on count mod 4
        remainder = count % 4

        if remainder == 1:  # 1, 5, 9...
            player.actions += 3
        elif remainder == 2:  # 2, 6, 10...
            game_state.draw_cards(player, 3)
        elif remainder == 3:  # 3, 7, 11...
            player.coins += 3
        elif remainder == 0 and count > 0:  # 4, 8, 12...
            player.buys += 3
        # count == 0 does nothing (shouldn't happen when playing it)
