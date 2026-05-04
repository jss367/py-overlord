"""Monastery — $2 Night.

For each card you've gained this turn, you may trash a card from hand or
a Copper in play.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Monastery(Card):
    def __init__(self):
        super().__init__(
            name="Monastery",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        gained = getattr(player, "cards_gained_this_turn_count", 0)
        if gained <= 0:
            return
        # Choices: cards in hand + Coppers in play
        coppers_in_play = [c for c in player.in_play if c.name == "Copper"]
        choices = list(player.hand) + coppers_in_play
        if not choices:
            return
        to_trash = player.ai.choose_cards_to_trash_for_monastery(
            game_state, player, choices, gained
        )
        for card in to_trash[:gained]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
            elif card in player.in_play:
                player.in_play.remove(card)
                game_state.trash_card(player, card)
