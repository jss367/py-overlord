from ..base_card import Card, CardCost, CardStats, CardType


class Prince(Card):
    """Sets aside an Action to be replayed every turn."""

    def __init__(self):
        super().__init__(
            name="Prince",
            cost=CardCost(coins=8),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside_card = None

    def play_effect(self, game_state):
        player = game_state.current_player
        affordable = [
            card for card in player.hand if card.is_action and card.cost.coins <= 4
        ]
        if not affordable:
            return
        choice = player.ai.choose_prince_target(game_state, player, affordable + [None])
        if choice is None or choice not in affordable:
            choice = affordable[0]
        player.hand.remove(choice)
        self.set_aside_card = choice
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        if not self.set_aside_card:
            self.duration_persistent = False
            return
        player = game_state.current_player
        card = self.set_aside_card
        player.in_play.append(card)
        card.on_play(game_state)
        if card in player.in_play:
            player.in_play.remove(card)
        if self not in player.duration:
            player.duration.append(self)
