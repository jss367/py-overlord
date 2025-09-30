"""Implementation of the Pawn choice card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Pawn(Card):
    def __init__(self):
        super().__init__(
            name="Pawn",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        choices = self._select_bonuses(player)

        for choice in choices:
            if choice == "card":
                game_state.draw_cards(player, 1)
            elif choice == "action":
                player.actions += 1
            elif choice == "buy":
                player.buys += 1
            elif choice == "coin":
                player.coins += 1

    @staticmethod
    def _select_bonuses(player) -> list[str]:
        options: list[str] = []

        if player.actions <= 1:
            options.append("action")
        options.append("card")

        if len(options) < 2:
            options.append("coin")

        if len(options) < 2:
            options.append("buy")

        return options[:2]
