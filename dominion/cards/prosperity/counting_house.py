from ..base_card import Card, CardCost, CardStats, CardType


class CountingHouse(Card):
    def __init__(self):
        super().__init__(
            name="Counting House",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        coppers = [c for c in player.discard if c.name == "Copper"]
        if not coppers:
            return
        chosen = player.ai.choose_coppers_for_counting_house(game_state, player, coppers)
        for copper in chosen:
            if copper in player.discard:
                player.discard.remove(copper)
                player.hand.append(copper)
