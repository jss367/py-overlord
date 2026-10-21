import random

from ..base_card import Card, CardCost, CardStats, CardType


class Inn(Card):
    def __init__(self):
        super().__init__(
            name="Inn",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2, cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ._discard import discard_from_hand

        discard_from_hand(game_state, game_state.current_player, 2, "inn")

    def on_gain(self, game_state, player):
        """Shuffle any Actions from the discard pile back into the deck."""

        super().on_gain(game_state, player)

        # Gather the action cards currently in the discard pile.
        action_cards = [card for card in player.discard if game_state.is_action(card)]

        if not action_cards:
            return

        # Remove the chosen cards from the discard pile.
        for card in action_cards:
            player.discard.remove(card)

        # Shuffle them into the current deck.
        player.deck.extend(action_cards)
        random.shuffle(player.deck)
