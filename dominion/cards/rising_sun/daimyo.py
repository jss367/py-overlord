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
        # Each Daimyo registers a pending replay; the action phase loop
        # replays whatever non-Command Action card is played next.
        pending = getattr(player, "daimyo_pending", 0)
        player.daimyo_pending = pending + 1
