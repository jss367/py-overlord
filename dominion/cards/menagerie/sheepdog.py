"""Sheepdog - Action-Reaction from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Sheepdog(Card):
    """+2 Cards. When you gain a card you may play this from your hand."""

    def __init__(self):
        super().__init__(
            name="Sheepdog",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def react_to_own_gain(self, game_state, player, gained_card) -> bool:
        """Hook used by gain handler. Owner may play this from hand."""
        if self not in player.hand:
            return False
        if not player.ai.should_play_sheepdog(game_state, player, gained_card):
            return False

        return game_state.play_action_from_hand_indirectly(player, self)
