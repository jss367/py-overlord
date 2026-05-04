"""Hideout: Action ($4). +1 Card. +2 Actions.

Trash a card from your hand. If it's a Victory card, gain a Curse.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Hideout(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Hideout",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None:
            # Mandatory trash — pick junk.
            choice = min(
                player.hand,
                key=lambda c: (
                    0 if c.name == "Curse" else (1 if c.name == "Copper" else 2),
                    c.cost.coins,
                    c.name,
                ),
            )
        if choice not in player.hand:
            return
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        if choice.is_victory and game_state.supply.get("Curse", 0) > 0:
            game_state.give_curse_to_player(player)
