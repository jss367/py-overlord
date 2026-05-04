from ..base_card import Card, CardCost, CardStats, CardType


class Tanuki(Card):
    """Action-Shadow ($5): Trash a card from your hand. Gain a card costing
    up to $2 more than it (Remodel-style).
    """

    def __init__(self):
        super().__init__(
            name="Tanuki",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.SHADOW],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if not player.hand:
            return

        trashed = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if trashed is None or trashed not in player.hand:
            return

        trashed_cost = game_state.get_card_cost(player, trashed)
        player.hand.remove(trashed)
        game_state.trash_card(player, trashed)

        max_cost = trashed_cost + 2
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.potions > 0:
                continue
            cost = game_state.get_card_cost(player, card)
            if cost > max_cost:
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
