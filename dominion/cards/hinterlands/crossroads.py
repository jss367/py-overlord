from ..base_card import Card, CardCost, CardStats, CardType


class Crossroads(Card):
    def __init__(self):
        super().__init__(
            name="Crossroads",
            cost=CardCost(coins=2),
            stats=CardStats(cards=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        victory_cards = sum(1 for card in player.hand if card.is_victory)
        player.actions += victory_cards

        player.crossroads_played += 1
        if player.crossroads_played == 1:
            player.buys += 1
