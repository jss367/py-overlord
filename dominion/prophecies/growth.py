"""Growth Prophecy."""

from dataclasses import dataclass

from .base_prophecy import Prophecy
from .registry import register


@register
@dataclass
class Growth(Prophecy):
    name: str = "Growth"
    description: str = (
        "While active: when you gain a Treasure, gain a cheaper card. "
        "(Can chain: gaining the cheaper Treasure can trigger again.)"
    )

    def on_gain(self, game_state, player, card) -> None:
        from dominion.cards.registry import get_card

        if not card.is_treasure:
            return
        triggered_cost = game_state.get_card_cost(player, card)

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                candidate = get_card(name)
            except ValueError:
                continue
            if candidate.cost.debt > 0 or candidate.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, candidate) >= triggered_cost:
                continue
            if not candidate.may_be_bought(game_state):
                continue
            candidates.append(candidate)

        if not candidates:
            return
        chosen = player.ai.choose_buy(game_state, candidates + [None])
        # Per rulebook: "This is not optional; if you gain a Treasure, you
        # have to gain a cheaper card if you can."
        if chosen is None:
            chosen = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(chosen.name, 0) <= 0:
            return
        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
