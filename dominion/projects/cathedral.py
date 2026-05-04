"""Cathedral project: at the start of your turn, trash a card from your hand."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class Cathedral(Project):
    def __init__(self) -> None:
        super().__init__("Cathedral", CardCost(coins=3))

    def on_turn_start(self, game_state, player) -> None:
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if choice is None:
            # Cathedral is mandatory — pick the cheapest junky card so the
            # AI can't no-op out of it.
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
