"""Swashbuckler: Action ($5). +3 Cards.

If your discard is non-empty, +1 Coffers; if you then have $4+ in
Coffers, take the Treasure Chest artifact.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Swashbuckler(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Swashbuckler",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if player.discard:
            player.coin_tokens += 1
            if player.coin_tokens >= 4:
                game_state.take_artifact(player, "Treasure Chest")
