from ..base_card import Card, CardCost, CardStats, CardType


class Loan(Card):
    def __init__(self):
        super().__init__(
            name="Loan",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed = []
        while player.deck or player.discard:
            if not player.deck:
                player.shuffle_discard_into_deck()
            card = player.deck.pop()
            if card.is_treasure:
                game_state.trash_card(player, card)
                break
            revealed.append(card)
        player.discard.extend(revealed)
