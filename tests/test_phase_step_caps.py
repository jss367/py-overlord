"""Mid-turn safety caps for phase loops.

The phase handlers (`handle_action_phase`, `handle_treasure_phase`,
`handle_buy_phase`, `handle_night_phase`) iterate in `while True:` loops with
no bound on the number of plays per turn. A genome that produces a card
whose play keeps replenishing the hand and granting +Actions can hang the
simulator indefinitely — the existing `turn_number > 100` cap in
`is_game_over` only fires at turn boundaries.

These tests pin a per-phase step cap that raises ``PhaseStepLimitExceeded``
on runaway, so the trainer's existing exception handler scores the offender
as ``-inf`` instead of hanging the worker.
"""

from dominion.cards.base_card import Card, CardCost, CardStats, CardType
from dominion.game.game_state import GameState, PhaseStepLimitExceeded
from dominion.game.player_state import PlayerState
from tests.utils import ChooseFirstActionAI


class _SelfReplenishingAction(Card):
    """Pathological action: returns to hand on play and grants +1 Action.

    Net effect per play: +1 Action and hand size unchanged → the action
    phase loop would iterate forever without a cap.
    """

    def __init__(self):
        super().__init__(
            name="_LoopCard",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def on_play(self, game_state):
        player = game_state.current_player
        player.actions += 1
        if self in player.in_play:
            player.in_play.remove(self)
        player.hand.append(self)


def test_action_phase_step_cap_aborts_runaway():
    ai = ChooseFirstActionAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([])
    state.phase = "action"

    player.hand = [_SelfReplenishingAction()]
    player.actions = 1

    try:
        state.handle_action_phase()
    except PhaseStepLimitExceeded as exc:
        assert "action" in str(exc).lower()
        return
    raise AssertionError(
        "handle_action_phase did not raise PhaseStepLimitExceeded on a "
        "self-replenishing action card; the cap is missing or too high."
    )
