from ..base_card import Card, CardCost, CardStats, CardType


class Treasury(Card):
    def __init__(self):
        super().__init__(
            name="Treasury",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION],
        )

    def on_buy_phase_end(self, game_state):
        player = game_state.current_player
        if getattr(player, "gained_victory_this_buy_phase", False):
            return
        if not player.ai.should_topdeck_treasury(game_state, player):
            return
        if self in player.in_play:
            player.in_play.remove(self)
            player.deck.insert(0, self)
