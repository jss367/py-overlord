from ..base_card import Card, CardCost, CardStats, CardType


class Weaver(Card):
    def __init__(self):
        super().__init__(
            name="Weaver",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        affordable = [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= 4
        ]

        chosen = None
        if affordable:
            chosen = player.ai.choose_buy(game_state, affordable + [None])
        if chosen:
            if game_state.supply.get(chosen.name, 0) > 0:
                game_state.supply[chosen.name] -= 1
                game_state.gain_card(player, chosen)
            return

        for _ in range(2):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))
