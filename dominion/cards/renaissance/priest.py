"""Priest: Action ($4). +$2. Trash a card from your hand.

For the rest of this turn, when you trash a card, +$2.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Priest(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Priest",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.hand:
            choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
            if choice is None:
                # Mandatory — pick junk.
                choice = min(
                    player.hand,
                    key=lambda c: (
                        0 if c.name == "Curse" else (1 if c.name == "Copper" else 2),
                        c.cost.coins,
                        c.name,
                    ),
                )
            if choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)

        # The "rest of turn" trigger only applies AFTER Priest's own trash.
        player.priest_played_this_turn = (
            getattr(player, "priest_played_this_turn", 0) + 1
        )
