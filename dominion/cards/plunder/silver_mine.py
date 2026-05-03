"""Silver Mine from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class SilverMine(Card):
    """$5 Treasure: $1. When you discard this from play, gain a Silver to your hand."""

    def __init__(self):
        super().__init__(
            name="Silver Mine",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def on_discard_from_play(self, game_state, player):
        from ..registry import get_card

        if game_state.supply.get("Silver", 0) <= 0:
            return

        game_state.supply["Silver"] -= 1
        gained = game_state.gain_card(player, get_card("Silver"))
        if gained in player.discard:
            player.discard.remove(gained)
            player.hand.append(gained)
        elif gained in player.deck:
            player.deck.remove(gained)
            player.hand.append(gained)
