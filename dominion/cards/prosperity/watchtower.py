from ..base_card import Card, CardCost, CardStats, CardType


class Watchtower(Card):
    def __init__(self):
        super().__init__(
            name="Watchtower",
            cost=CardCost(coins=3),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        discard_count = len(player.hand)
        player.discard.extend(player.hand)
        player.hand = []
        player.coins += discard_count

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if self in player.discard:
            player.discard.remove(self)
            player.deck.append(self)
