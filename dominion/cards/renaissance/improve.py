"""Improve: Action ($3). +$2.

At the start of Cleanup, you may trash an Action card you would discard
from play this turn, to gain a card costing exactly $1 more.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Improve(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Improve",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def on_cleanup_start(self, game_state):
        player = game_state.current_player
        # Find Action cards currently in play that aren't going to remain
        # in play (durations stay; multiplied durations stay).
        durations = set(player.duration + player.multiplied_durations)
        candidates = [
            c
            for c in player.in_play
            if c.is_action and c not in durations and c is not self
        ]
        if not candidates:
            return

        # Heuristic: trash the cheapest non-payload Action to upgrade.
        target = min(
            candidates,
            key=lambda c: (
                c.cost.coins,
                c.stats.cards + c.stats.actions + c.stats.coins,
                c.name,
            ),
        )

        # Find a card costing exactly $1 more in supply.
        from ..registry import get_card

        upgrade_cost = target.cost.coins + 1
        gain_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            cand = get_card(name)
            if cand.cost.coins == upgrade_cost and cand.cost.potions == target.cost.potions:
                gain_options.append(cand)

        if not gain_options:
            return

        # Trash the target action.
        if target in player.in_play:
            player.in_play.remove(target)
        game_state.trash_card(player, target)

        gain = max(
            gain_options,
            key=lambda c: (c.is_action, c.is_treasure, c.stats.cards, c.cost.coins, c.name),
        )
        if game_state.supply.get(gain.name, 0) <= 0:
            return
        game_state.supply[gain.name] -= 1
        game_state.gain_card(player, gain)
