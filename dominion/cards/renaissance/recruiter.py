"""Recruiter: Action ($5). +2 Cards. Trash a card from your hand.
+1 Villager per $1 it cost."""

from ..base_card import Card, CardCost, CardStats, CardType


class Recruiter(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Recruiter",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None:
            # Mandatory trash — pick something safe (junk first; otherwise
            # cheapest non-treasure to extract a Villager without losing
            # too much value).
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
        cost = choice.cost.coins
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        player.villagers += cost
