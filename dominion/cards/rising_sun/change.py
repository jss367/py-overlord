from ..base_card import Card, CardCost, CardStats, CardType


class Change(Card):
    """Action ($4): If you have any Debt, +$3.
    Otherwise, trash a card from your hand and gain a card costing more $;
    take Debt equal to the difference in coin cost.
    """

    def __init__(self):
        super().__init__(
            name="Change",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if player.debt > 0:
            player.coins += 3
            return

        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if trash_choice is None or trash_choice not in player.hand:
            return

        trashed_cost = game_state.get_card_cost(player, trash_choice)
        player.hand.remove(trash_choice)
        game_state.trash_card(player, trash_choice)

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
            if cost <= trashed_cost:
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

        new_cost = game_state.get_card_cost(player, chosen)
        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
        debt_to_take = max(0, new_cost - trashed_cost)
        player.debt += debt_to_take
