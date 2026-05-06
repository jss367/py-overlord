"""Ratcatcher (Adventures) — $2 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class Ratcatcher(Card):
    def __init__(self):
        super().__init__(
            name="Ratcatcher",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "start_of_turn":
            return False
        if not player.hand:
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        target = player.ai.choose_card_to_set_aside_for_ratcatcher(
            game_state, player, list(player.hand)
        )
        if target is None or target not in player.hand:
            return False
        player.hand.remove(target)
        game_state.trash_card(player, target)
        game_state.call_from_tavern(player, self)
        return True
