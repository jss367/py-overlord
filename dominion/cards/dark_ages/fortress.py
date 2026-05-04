"""Fortress — $4 Village-style card that returns to hand when trashed."""

from ..base_card import Card, CardCost, CardStats, CardType


class Fortress(Card):
    """+1 Card +2 Actions.

    When you trash this, put it into your hand instead of trashing it.
    """

    def __init__(self):
        super().__init__(
            name="Fortress",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def on_trash(self, game_state, player):
        # Move from trash back to hand. The trash list was just appended in
        # GameState.trash_card; remove it and move to hand.
        if self in game_state.trash:
            game_state.trash.remove(self)
        # Defensive: if it lingers in any zone, remove it.
        if self in player.in_play:
            player.in_play.remove(self)
        if self in player.discard:
            player.discard.remove(self)
        if self in player.deck:
            player.deck.remove(self)
        # And put into hand
        if self not in player.hand:
            player.hand.append(self)
