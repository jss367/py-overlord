from ..base_card import Card, CardCost, CardStats, CardType


class Daimyo(Card):
    """Action-Command ($6 Debt): +1 Card, +1 Action.
    The next time this turn you play a non-Command Action card, replay it.

    Multiple Daimyos stack: each replays the next non-Command Action play.
    Pure-debt cost: buying takes 6 Debt.
    """

    def __init__(self):
        super().__init__(
            name="Daimyo",
            cost=CardCost(coins=0, debt=6),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.COMMAND],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Bind "this turn" to the actual turn, including off-turn plays.
        owner = game_state.turn_player
        marker = (game_state.turn_number, owner.turns_taken, owner)
        previous = player.daimyo_turn
        if previous is not None and (
            previous[:2] != marker[:2] or previous[2] is not owner
        ) or previous is None and player is not owner:
            player.daimyo_pending = 0
            player.daimyo_sources = []
        player.daimyo_turn = marker
        player.daimyo_pending += 1
        player.daimyo_sources.append(self)
