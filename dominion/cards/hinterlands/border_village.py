from ..base_card import Card, CardCost, CardStats, CardType


class BorderVillage(Card):
    def __init__(self):
        super().__init__(
            name="Border Village",
            cost=CardCost(coins=6),
            stats=CardStats(actions=2, cards=1),
            types=[CardType.ACTION],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        from ..registry import get_card

        options: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins < self.cost.coins:
                options.append(card)

        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if not choice:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
