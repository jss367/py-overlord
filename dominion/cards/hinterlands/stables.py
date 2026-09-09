"""Stables ($5): you may discard a Treasure, for +3 Cards and +1 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Stables(Card):
    def __init__(self):
        super().__init__(
            name="Stables",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures = [card for card in player.hand if card.is_treasure]
        if not treasures:
            return

        choice = player.ai.choose_treasure_to_discard_for_stables(
            game_state, player, list(treasures)
        )
        if choice is None or choice not in treasures:
            return
        player.hand.remove(choice)
        game_state.discard_card(player, choice)

        game_state.draw_cards(player, 3)
        player.actions += 1
