"""Grotto from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Grotto(Card):
    """$2 Action-Duration: +1 Action. Set aside up to 4 cards from your hand.
    At the start of your next turn, discard them, then draw that many.
    """

    def __init__(self):
        super().__init__(
            name="Grotto",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player

        for _ in range(4):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_set_aside(
                game_state, player, list(player.hand) + [None], reason="grotto"
            )
            if choice is None or choice not in player.hand:
                break
            player.hand.remove(choice)
            self.set_aside.append(choice)

        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player

        count = len(self.set_aside)
        for card in self.set_aside:
            game_state.discard_card(player, card)
        self.set_aside = []

        if count > 0:
            game_state.draw_cards(player, count)

        self.duration_persistent = False
