"""Implementation of the Feast (1E) card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Feast(Card):
    """Action ($4): Trash this card. Gain a card costing up to $5."""

    def __init__(self):
        super().__init__(
            name="Feast",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        # Trash this card. (It's currently in_play because on_play moved it.)
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.trash_card(player, self)

        # Gain a card costing up to $5.
        options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.cost.coins > 5:
                continue
            if candidate.cost.potions > 0 or candidate.cost.debt > 0:
                continue
            options.append(candidate)

        if not options:
            return

        chosen = player.ai.choose_buy(game_state, options + [None])
        if chosen is None or chosen not in options:
            chosen = max(options, key=lambda c: (c.cost.coins, c.is_action, c.name))

        if game_state.supply.get(chosen.name, 0) > 0:
            game_state.supply[chosen.name] -= 1
            game_state.gain_card(player, chosen)
