from ..base_card import Card, CardCost, CardStats, CardType


class Island(Card):
    """Action-Victory ($4): Move this and another card from your hand onto your
    Island mat. Worth 2 VP.
    """

    def __init__(self):
        super().__init__(
            name="Island",
            cost=CardCost(coins=4),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Move this Island onto the Island mat.
        if self in player.in_play:
            player.in_play.remove(self)
            player.island_mat.append(self)

        # Move another card from hand to the mat.
        if not player.hand:
            return

        choice = player.ai.choose_card_to_set_aside_for_island(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        player.island_mat.append(choice)
