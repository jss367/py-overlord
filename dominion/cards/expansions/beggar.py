from ..base_card import Card, CardCost, CardStats, CardType
from ..registry import get_card


class Beggar(Card):
    def __init__(self):
        super().__init__(
            name="Beggar",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for _ in range(3):
            if game_state.supply.get("Copper", 0) > 0:
                game_state.supply["Copper"] -= 1
                copper = get_card("Copper")
                player.hand.append(copper)
                copper.on_gain(game_state, player)
