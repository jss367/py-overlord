"""Implementation of the Inventor cost reducer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Inventor(Card):
    def __init__(self):
        super().__init__(
            name="Inventor",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        choices = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                choices.append(card)

        if choices:
            choices.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            gain = choices[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)

        player.cost_reduction += 1
