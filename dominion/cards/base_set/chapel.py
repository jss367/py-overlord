from ..base_card import Card, CardCost, CardStats, CardType


class Chapel(Card):
    def __init__(self):
        super().__init__(
            name="Chapel",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        """Trash up to 4 cards from your hand."""
        player = game_state.current_player

        # Let AI determine which cards to trash
        cards_to_trash = []

        # Simulate up to 4 trash decisions
        for _ in range(4):
            if not player.hand:
                break

            # Let AI choose a card to trash
            card_to_trash = player.ai.choose_card_to_trash(game_state, player.hand)

            if card_to_trash:
                player.hand.remove(card_to_trash)
                game_state.trash.append(card_to_trash)
                cards_to_trash.append(card_to_trash)
            else:
                # AI chose to stop trashing
                break

        # Logging for potential debugging
        game_state.log(f"{player.ai} trashed {len(cards_to_trash)} cards")
