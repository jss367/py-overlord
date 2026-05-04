"""Implementation of the Bazaar card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Bazaar(Card):
    """Action ($5): +1 Card, +2 Actions, +$1.

    Bazaar is purely a stat card by the rules — there are no extra effects
    beyond the +1 Card / +2 Actions / +$1 already declared on
    :class:`CardStats`. The empty :meth:`play_effect` override is here to
    keep the seaside expansion uniform with the other Action implementations
    (every card has a ``play_effect`` for ease of grepping / auditing).
    """

    def __init__(self):
        super().__init__(
            name="Bazaar",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=2, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        # Stat-only card; all bonuses are applied via CardStats in on_play.
        return
