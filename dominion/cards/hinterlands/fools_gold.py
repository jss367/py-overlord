from ..base_card import Card, CardCost, CardStats, CardType


class FoolsGold(Card):
    def __init__(self):
        super().__init__(
            name="Fool's Gold",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.fools_gold_played >= 1:
            player.coins += 4
        else:
            player.coins += 1

        player.fools_gold_played += 1
