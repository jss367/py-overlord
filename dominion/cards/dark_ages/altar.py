"""Altar — $6 Action that trashes from hand and gains a $5 card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Altar(Card):
    """Trash a card from your hand. Gain a card costing up to $5."""

    def __init__(self):
        super().__init__(
            name="Altar",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        if player.hand:
            choice = player.ai.choose_card_to_trash_for_altar(
                game_state, player, list(player.hand)
            )
            if choice and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        # Gain a card costing up to $5
        candidates: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                c = get_card(name)
            except ValueError:
                continue
            if c.cost.potions > 0 or c.cost.debt > 0:
                continue
            cost = game_state.get_card_cost(player, c)
            if cost <= 5 and c.may_be_bought(game_state):
                candidates.append(c)

        choice = player.ai.choose_card_to_gain_with_altar(
            game_state, player, candidates
        )
        if choice and game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, get_card(choice.name))
