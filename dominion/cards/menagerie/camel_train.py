"""Camel Train - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class CamelTrain(Card):
    """Exile a non-Victory card from the Supply. When you gain this, exile a
    Gold from the Supply.
    """

    def __init__(self):
        super().__init__(
            name="Camel Train",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        # Choose a non-Victory card from supply with at least 1 in pile.
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_victory:
                continue
            candidates.append(card)
        if not candidates:
            return

        # Prefer most expensive non-Victory (Gold strongest)
        candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        chosen = candidates[0]
        game_state.supply[chosen.name] -= 1
        player.exile.append(chosen)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        if game_state.supply.get("Gold", 0) <= 0:
            return
        game_state.supply["Gold"] -= 1
        player.exile.append(get_card("Gold"))
