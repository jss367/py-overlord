"""Implementation of Secret Passage."""

from ..base_card import Card, CardCost, CardStats, CardType


class SecretPassage(Card):
    """+2 Cards +1 Action. Take a card from your hand and put it anywhere
    in your deck."""

    def __init__(self):
        super().__init__(
            name="Secret Passage",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        chosen = player.ai.choose_card_to_place_for_secret_passage(
            game_state, player, list(player.hand)
        )
        if chosen is None or chosen not in player.hand:
            return

        player.hand.remove(chosen)
        position = player.ai.choose_secret_passage_position(
            game_state, player, chosen, len(player.deck)
        )
        # Clamp the index to a valid range.
        if position < 0:
            position = 0
        if position > len(player.deck):
            position = len(player.deck)
        player.deck.insert(position, chosen)
