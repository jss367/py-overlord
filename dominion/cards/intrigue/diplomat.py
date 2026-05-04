"""Implementation of Diplomat."""

from ..base_card import Card, CardCost, CardStats, CardType


class Diplomat(Card):
    """+2 Cards. If you have 5 or fewer cards in hand (after drawing),
    +2 Actions.

    Reaction: When another player plays an Attack, you may first reveal
    this from a hand of 5 or more cards, to draw 2 cards then discard 3.

    The Reaction logic lives in ``GameState._maybe_react_diplomat`` (fires
    just before each Attack resolves on the target).
    """

    def __init__(self):
        super().__init__(
            name="Diplomat",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # +2 Cards already applied via base stats. The "5 or fewer cards
        # in hand AFTER drawing" check uses the post-draw hand size.
        if len(player.hand) <= 5:
            player.actions += 2
