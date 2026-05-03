from ..base_card import Card, CardCost, CardStats, CardType


class Tactician(Card):
    """Action-Duration ($5): If you have at least one card in hand: discard your hand,
    and at the start of your next turn, +5 Cards, +1 Buy, +1 Action.
    """

    def __init__(self):
        super().__init__(
            name="Tactician",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = False
        self.activated = False

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            self.activated = False
            return

        # Discard the entire hand.
        hand_to_discard = list(player.hand)
        player.hand = []
        for card in hand_to_discard:
            game_state.discard_card(player, card)

        self.activated = True
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player

        if self.activated:
            game_state.draw_cards(player, 5)
            player.actions += 1
            player.buys += 1

        self.activated = False
        self.duration_persistent = False
