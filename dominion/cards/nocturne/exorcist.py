"""Exorcist — $4 Night.

Trash a card from hand. Gain a cheaper card from one of the Spirit piles.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Exorcist(Card):
    nocturne_piles = {
        "Will-o'-Wisp": 12,
        "Imp": 13,
        "Ghost": 6,
    }

    def __init__(self):
        super().__init__(
            name="Exorcist",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return
        trashed = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if trashed is None or trashed not in player.hand:
            return
        player.hand.remove(trashed)
        game_state.trash_card(player, trashed)

        # Gain only from the three Spirit piles, which are not buyable.
        options = []
        for name in self.nocturne_piles:
            count = game_state.supply.get(name, 0)
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins >= trashed.cost.coins:
                continue
            options.append(card)
        if not options:
            return
        choice = player.ai.choose_card_to_gain_for_exorcist(
            game_state, player, trashed, options
        )
        if choice is None or choice.name not in {c.name for c in options}:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.cards, c.name))
        if game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, choice)
