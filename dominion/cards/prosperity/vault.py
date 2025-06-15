from ..base_card import Card, CardCost, CardStats, CardType


class Vault(Card):
    def __init__(self):
        super().__init__(
            name="Vault",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        discard_count = len(player.hand)
        player.discard.extend(player.hand)
        player.hand = []
        player.coins += discard_count

        for other in game_state.players:
            if other is player or not other.hand:
                continue
            discard = other.hand[:1]
            other.discard.extend(discard)
            for c in discard:
                other.hand.remove(c)
            other.draw_cards(1)
