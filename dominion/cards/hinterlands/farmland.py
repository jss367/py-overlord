from ..base_card import Card, CardCost, CardStats, CardType


class Farmland(Card):
    def __init__(self):
        super().__init__(
            name="Farmland",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.VICTORY],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)

        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if not to_trash:
            to_trash = min(player.hand, key=lambda card: (card.cost.coins, card.name))

        if to_trash not in player.hand:
            return

        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        target_cost = to_trash.cost.coins + 2
        if target_cost < 0:
            return

        from ..registry import get_card

        options = [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins == target_cost
        ]

        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if not choice:
            choice = options[0]

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)
