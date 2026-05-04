"""Madman — non-supply Action that returns to its pile after play."""

from ..base_card import Card, CardCost, CardStats, CardType


class Madman(Card):
    """+2 Actions. Return this to the Madman pile, then +1 Card per card in hand.

    Madman is a non-supply card. It only ever enters a player's deck via
    Hermit's "trash to gain a Madman" effect at end of buy phase.
    """

    def __init__(self):
        super().__init__(
            name="Madman",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def starting_supply(self, game_state) -> int:
        return 0  # not in supply

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        player.actions += 2

        # Return Madman to the Madman pile (non-supply pile).
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.supply["Madman"] = game_state.supply.get("Madman", 0) + 1

        # +1 Card per card in hand
        if player.hand:
            game_state.draw_cards(player, len(player.hand))
