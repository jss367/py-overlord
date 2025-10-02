from ..base_card import Card, CardCost, CardStats, CardType


class Harvest(Card):
    """Counts distinct cards from the top of the deck for coins."""

    def __init__(self):
        super().__init__(
            name="Harvest",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []

        for _ in range(4):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if revealed:
            unique_names = len({card.name for card in revealed})
            player.coins += unique_names
            game_state.discard_cards(player, revealed)
