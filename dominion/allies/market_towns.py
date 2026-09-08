from .base_ally import Ally


class MarketTowns(Ally):
    def __init__(self):
        super().__init__("Market Towns")

    def on_buy_phase_start(self, game_state, player):
        from ..game.game_state import PHASE_STEP_LIMIT, PhaseStepLimitExceeded

        for _ in range(PHASE_STEP_LIMIT):
            if not player.favors or not game_state._voyage_can_play_from_hand(player):
                return
            choices = [
                c
                for c in player.hand
                if c.is_action and not game_state._warlord_blocks_action_play(player, c)
            ]
            choice = player.ai.choose_action(game_state, choices + [None])
            if choice not in choices:
                return
            player.favors -= 1
            game_state.play_action_from_hand_indirectly(player, choice)
        raise PhaseStepLimitExceeded("Market Towns exceeded play limit")
