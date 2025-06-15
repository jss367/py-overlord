from ..base_card import Card, CardCost, CardStats, CardType


class GrandMarket(Card):
    def __init__(self):
        super().__init__(
            name="Grand Market",
            cost=CardCost(coins=6),
            stats=CardStats(actions=1, cards=1, buys=1, coins=2),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:
        player = game_state.current_player
        if any(card.name == "Copper" for card in player.in_play):
            return False
        return super().may_be_bought(game_state)
