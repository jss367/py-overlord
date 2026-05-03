from ..base_card import Card, CardCost, CardStats, CardType


class Haven(Card):
    """Action-Duration ($2): +1 Card, +1 Action. Set aside a card from your hand
    face down (under this). At the start of your next turn, put it into your hand.
    """

    def __init__(self):
        super().__init__(
            name="Haven",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside = None
        self.duration_persistent = False

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        choice = player.ai.choose_card_to_set_aside_for_haven(
            game_state, player, list(player.hand)
        )
        if choice is None or choice not in player.hand:
            # No card chosen — Haven still goes to duration but with nothing set aside
            choice = None

        if choice is not None:
            player.hand.remove(choice)
            self.set_aside = choice

        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside is not None:
            player.hand.append(self.set_aside)
            self.set_aside = None
        self.duration_persistent = False
