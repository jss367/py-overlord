from ..base_card import Card, CardCost, CardStats, CardType


class Venture(Card):
    def __init__(self):
        super().__init__(
            name="Venture",
            cost=CardCost(coins=5),
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
                player.in_play.append(card)
                card.on_play(game_state)
                break
            revealed.append(card)
        player.discard.extend(revealed)
