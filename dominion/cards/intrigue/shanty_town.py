"""Implementation of Shanty Town."""

from ..base_card import Card, CardCost, CardStats, CardType


class ShantyTown(Card):
    """+2 Actions. Reveal your hand. If you have no Action cards in hand,
    +2 Cards."""

    def __init__(self):
        super().__init__(
            name="Shanty Town",
            cost=CardCost(coins=3),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # "Reveal your hand": no game effect besides allowing the bonus.
        # If no Action cards in hand (after Shanty Town has left), +2 Cards.
        if not any(card.is_action for card in player.hand):
            game_state.draw_cards(player, 2)
