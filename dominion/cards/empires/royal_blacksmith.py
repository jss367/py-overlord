from ..base_card import Card, CardCost, CardStats, CardType


class RoyalBlacksmith(Card):
    def __init__(self):
        super().__init__(
            name="Royal Blacksmith",
            cost=CardCost(coins=8),
            stats=CardStats(cards=5),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        coppers = [card for card in player.hand if card.name == "Copper"]
        for copper in coppers:
            player.hand.remove(copper)
            player.discard.append(copper)
