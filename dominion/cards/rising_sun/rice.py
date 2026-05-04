from ..base_card import Card, CardCost, CardStats, CardType


class Rice(Card):
    """Treasure ($7): +1 Buy.
    +$1 per different type among cards you have in play.
    """

    def __init__(self):
        super().__init__(
            name="Rice",
            cost=CardCost(coins=7),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        type_set = set()
        for card in player.in_play + player.duration:
            for t in card.types:
                type_set.add(t)
        player.coins += len(type_set)
