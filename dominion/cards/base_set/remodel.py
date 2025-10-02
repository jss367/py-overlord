"""Implementation of the Remodel trasher."""

from ..base_card import Card, CardCost, CardStats, CardType


class Remodel(Card):
    def __init__(self):
        super().__init__(
            name="Remodel",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if trash_choice not in player.hand:
            trash_choice = min(player.hand, key=self._trash_priority)

        if trash_choice not in player.hand:
            return

        player.hand.remove(trash_choice)
        game_state.trash_card(player, trash_choice)

        self._gain_replacement(game_state, player, trash_choice)

    def _gain_replacement(self, game_state, player, trashed):
        max_coins = trashed.cost.coins + 2
        max_potions = trashed.cost.potions

        from ..registry import get_card

        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.cost.potions > max_potions:
                continue
            if candidate.cost.coins > max_coins:
                continue
            options.append(candidate)

        if not options:
            return

        choice = player.ai.choose_buy(game_state, options + [None])
        if choice not in options:
            options.sort(
                key=lambda c: (c.cost.coins, c.cost.potions, c.stats.cards, c.name),
                reverse=True,
            )
            choice = options[0]

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, choice)

    @staticmethod
    def _trash_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
