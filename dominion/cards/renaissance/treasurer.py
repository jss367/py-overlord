"""Treasurer: Action ($5). +$3.

Choose one: trash a Treasure from your hand; gain a Treasure from the
trash to your hand; or take the Key artifact.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Treasurer(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Treasurer",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        key = game_state.artifacts.get("Key")
        treasures_in_trash = [c for c in game_state.trash if c.is_treasure]
        treasures_in_hand = [c for c in player.hand if c.is_treasure]

        # Decision priority: take the Key if we don't already hold it,
        # otherwise gain a treasure from the trash if any exist, otherwise
        # trash a Copper from hand.
        if key is not None and key.holder is not player:
            game_state.take_artifact(player, "Key")
            return

        if treasures_in_trash:
            best = max(treasures_in_trash, key=lambda c: (c.cost.coins, c.name))
            game_state.trash.remove(best)
            player.hand.append(best)
            return

        if treasures_in_hand:
            choice = min(treasures_in_hand, key=lambda c: (c.cost.coins, c.name))
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
