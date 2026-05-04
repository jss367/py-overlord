"""Faithful Hound — $2 Action-Reaction.

+2 Cards. When you discard this other than during Cleanup, you may set it
aside; if you do, put it into hand at end of turn.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class FaithfulHound(Card):
    def __init__(self):
        super().__init__(
            name="Faithful Hound",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def react_to_discard(self, game_state, player):
        """Move the Hound into pending_blessed_boons-like staging.

        The simulator already calls this hook in ``_handle_discard_reactions``
        for any card with ``react_to_discard``. We set the card aside (remove
        from discard), and a one-shot ``hound_set_aside`` list on the player
        will return it to hand at the start of cleanup.
        """

        if self in player.discard:
            player.discard.remove(self)
            if not hasattr(player, "hound_set_aside"):
                player.hound_set_aside = []
            player.hound_set_aside.append(self)
