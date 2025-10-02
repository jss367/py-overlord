from ..base_card import Card, CardCost, CardStats, CardType


class HuntingParty(Card):
    """Finds a card that is not already present in hand."""

    def __init__(self):
        super().__init__(
            name="Hunting Party",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []

        hand_names = {card.name for card in player.hand}

        while True:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break

            card = player.deck.pop()
            if card.name not in hand_names:
                player.hand.append(card)
                break

            revealed.append(card)

        if revealed:
            game_state.discard_cards(player, revealed)
