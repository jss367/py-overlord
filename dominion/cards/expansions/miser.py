from ..base_card import Card, CardCost, CardStats, CardType


class Miser(Card):
    def __init__(self):
        super().__init__(
            name="Miser",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        coppers_in_hand = [c for c in player.hand if c.name == "Copper"]
        if coppers_in_hand:
            chosen = player.ai.choose_card_to_trash(game_state, coppers_in_hand)
            if chosen:
                player.hand.remove(chosen)
                player.miser_coppers += 1
                return
        player.coins += player.miser_coppers
