from ..base_card import Card, CardCost, CardStats, CardType


class Villa(Card):
    def __init__(self):
        super().__init__(
            name="Villa",
            cost=CardCost(coins=4),
            stats=CardStats(actions=2, coins=1, buys=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        # Move only this gained copy, wherever the gain placed it.
        if game_state._remove_gained_card_from_zones(player, self, target=player.hand):
            player.hand.append(self)
        player.actions += 1
        if player is game_state.turn_player and game_state.phase in {"buy", "treasure"}:
            game_state.phase = "action"
