from ..base_card import Card, CardCost, CardStats, CardType


class Patrician(Card):
    def __init__(self):
        super().__init__(
            name="Patrician",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Reveal the top card of the deck; if it costs 5 or more, draw it
        if player.deck:
            top = player.deck[-1]
            if top.cost.coins >= 5:
                player.draw_cards(1)
        
