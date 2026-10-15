from ..base_card import Card, CardCost, CardStats, CardType


class FarmingVillage(Card):
    """Digs for an Action or Treasure while providing +2 Actions."""

    def __init__(self):
        super().__init__(
            name="Farming Village",
            cost=CardCost(coins=4),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []

        while True:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break

            card = player.deck.pop()
            if game_state.is_action(card) or game_state.is_treasure(card):
                player.hand.append(card)
                break

            revealed.append(card)

        if revealed:
            game_state.discard_cards(player, revealed)
