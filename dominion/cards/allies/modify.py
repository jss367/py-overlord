from ..base_card import Card, CardCost, CardStats, CardType


class Modify(Card):
    def __init__(self):
        super().__init__(
            name="Modify",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return
        to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if not to_trash:
            return
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)
        max_cost = to_trash.cost.coins + 2
        choices = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= max_cost
        ]
        if choices:
            gain = player.ai.choose_buy(game_state, [get_card(n) for n in choices])
            if gain:
                game_state.supply[gain.name] -= 1
                game_state.gain_card(player, gain)
