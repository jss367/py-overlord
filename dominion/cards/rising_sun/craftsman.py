from ..base_card import Card, CardCost, CardStats, CardType


class Craftsman(Card):
    """Action ($3): +2 Debt. Gain a card costing up to $5.

    "Up to $5" excludes any card with Debt in its cost.
    """

    def __init__(self):
        super().__init__(
            name="Craftsman",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        player.debt += 2

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            # "Up to $5" excludes cards with Debt in their cost.
            if card.cost.debt > 0:
                continue
            if card.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, card) > 5:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return

        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
