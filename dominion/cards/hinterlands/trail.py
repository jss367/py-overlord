from ..base_card import Card, CardCost, CardStats, CardType


class Trail(Card):
    def __init__(self):
        super().__init__(
            name="Trail",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def _play_now(self, game_state, player):
        """Play Trail immediately from its current location."""

        # Remove the card from wherever it currently is.
        if self in player.discard:
            player.discard.remove(self)
        elif self in player.deck:
            player.deck.remove(self)
        elif self in player.hand:
            player.hand.remove(self)
        elif self in game_state.trash:
            game_state.trash.remove(self)
        else:
            return

        player.in_play.append(self)
        self.on_play(game_state)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        self._play_now(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        self._play_now(game_state, player)
