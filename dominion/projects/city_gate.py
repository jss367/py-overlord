"""City Gate: at the start of your turn, +1 Card; then put one card from your
hand on top of your deck."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class CityGate(Project):
    def __init__(self) -> None:
        super().__init__("City Gate", CardCost(coins=3))

    def on_turn_start(self, game_state, player) -> None:
        game_state.draw_cards(player, 1)
        if not player.hand:
            return
        choice = player.ai.choose_card_to_topdeck_from_hand(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            # Mandatory — fall back to a sensible default (junkiest card).
            choice = min(
                player.hand,
                key=lambda c: (
                    0 if c.is_victory and not c.is_action else 1,
                    c.cost.coins,
                    c.name,
                ),
            )
        if choice in player.hand:
            player.hand.remove(choice)
            player.deck.append(choice)
