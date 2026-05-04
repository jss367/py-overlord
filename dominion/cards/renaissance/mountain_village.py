"""Mountain Village: Action ($4). +2 Actions.

Look through your discard pile and put a card from it into your hand
(or +1 Card if your discard is empty).
"""

from ..base_card import Card, CardCost, CardStats, CardType


class MountainVillage(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Mountain Village",
            cost=CardCost(coins=4),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.discard:
            game_state.draw_cards(player, 1)
            return

        # Pick the most useful card from discard. Prefer Actions, then high
        # cost Treasures.
        best = max(
            player.discard,
            key=lambda c: (c.is_action, c.cost.coins, c.stats.cards, c.name),
        )
        player.discard.remove(best)
        player.hand.append(best)
