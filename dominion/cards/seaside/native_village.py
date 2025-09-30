"""Implementation of the Native Village mat mechanic."""

from ..base_card import Card, CardCost, CardStats, CardType


class NativeVillage(Card):
    def __init__(self):
        super().__init__(
            name="Native Village",
            cost=CardCost(coins=2),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.native_village_mat and len(player.hand) <= 4:
            player.hand.extend(player.native_village_mat)
            player.native_village_mat = []
            return

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if player.deck:
            card = player.deck.pop()
            player.native_village_mat.append(card)
