"""Cemetery — $4 Victory.

Worth 2 VP. When you gain this, you may trash up to 4 cards from hand.
Heirloom: Haunted Mirror.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Cemetery(Card):
    heirloom = "Haunted Mirror"

    def __init__(self):
        super().__init__(
            name="Cemetery",
            cost=CardCost(coins=4),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY, CardType.FATE],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if not player.hand:
            return
        chosen = player.ai.choose_cards_to_trash_for_cemetery(
            game_state, player, list(player.hand)
        )
        for card in chosen[:4]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
