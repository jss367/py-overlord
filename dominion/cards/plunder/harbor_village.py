"""Implementation of the Harbor Village card from Plunder."""

from ..base_card import Card, CardCost, CardStats, CardType


class HarborVillage(Card):
    """Harbor Village - Action ($4)

    +1 Card
    +2 Actions
    After the next Action card you play this turn, if it gave you +$, +$1.
    """

    def __init__(self):
        super().__init__(
            name="Harbor Village",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Track that the next action should grant +$1 if it gives +$
        if not hasattr(player, "harbor_village_pending"):
            player.harbor_village_pending = 0
        player.harbor_village_pending += 1
