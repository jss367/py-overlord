"""Displace - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Displace(Card):
    """Exile a card from your hand. Gain a differently named card costing up
    to $2 more than it, that is not a Duration card.
    """

    def __init__(self):
        super().__init__(
            name="Displace",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        choice = player.ai.choose_card_to_exile_for_sanctuary(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            choice = min(player.hand, key=self._exile_priority)
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        player.exile.append(choice)

        max_cost = choice.cost.coins + 2
        max_potions = choice.cost.potions

        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                candidate = get_card(name)
            except ValueError:
                continue
            if candidate.name == choice.name:
                continue
            if candidate.is_duration:
                continue
            if candidate.cost.coins > max_cost:
                continue
            if candidate.cost.potions > max_potions:
                continue
            options.append(candidate)

        if not options:
            return

        gain_choice = player.ai.choose_buy(game_state, options + [None])
        if gain_choice is None or gain_choice not in options:
            options.sort(
                key=lambda c: (c.cost.coins, c.cost.potions, c.stats.cards, c.name),
                reverse=True,
            )
            gain_choice = options[0]

        if game_state.supply.get(gain_choice.name, 0) <= 0:
            return
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, gain_choice)

    @staticmethod
    def _exile_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
