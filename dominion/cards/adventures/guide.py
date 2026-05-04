"""Guide (Adventures) — $3 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class Guide(Card):
    def __init__(self):
        super().__init__(
            name="Guide",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        if trigger != "start_of_turn":
            return False
        if not player.ai.should_call_from_tavern(
            game_state, player, self, trigger, *args
        ):
            return False
        # Discard hand and draw 5.
        if player.hand:
            hand = list(player.hand)
            player.hand = []
            game_state.discard_cards(player, hand, from_cleanup=False)
        game_state.draw_cards(player, 5)
        game_state.call_from_tavern(player, self)
        return True
