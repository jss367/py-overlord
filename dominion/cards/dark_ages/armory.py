"""Implementation of the Armory gainer."""

from ..base_card import Card, CardCost, CardStats, CardType


class Armory(Card):
    def __init__(self):
        super().__init__(
            name="Armory",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                options.append(card)

        if not options:
            return

        options.sort(key=lambda c: (c.cost.coins, c.stats.cards, c.name), reverse=True)
        gained = options[0]
        game_state.supply[gained.name] -= 1
        game_state.gain_card(game_state.current_player, gained, to_deck=True)
