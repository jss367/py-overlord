"""Imp — non-supply Action-Spirit, $2."""

from ...base_card import Card, CardCost, CardStats, CardType


class Imp(Card):
    """+2 Cards. You may play an Action from hand you don't have a copy of in play."""

    def __init__(self):
        super().__init__(
            name="Imp",
            cost=CardCost(coins=2),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.SPIRIT],
        )

    def starting_supply(self, game_state) -> int:
        return 13

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        in_play_names = {c.name for c in player.in_play}
        choices = [
            c for c in player.hand
            if c.is_action and c.name not in in_play_names
        ]
        if not choices:
            return
        choice = player.ai.choose_imp_action(game_state, player, choices)
        if choice is None or choice not in player.hand:
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        game_state.log_callback(
            ("action", player.ai.name, f"Imp plays {choice}", {})
        )
        choice.on_play(game_state)
        game_state.fire_ally_play_hooks(player, choice)
