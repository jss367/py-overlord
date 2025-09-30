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

        origin = None
        if self in player.discard:
            player.discard.remove(self)
            origin = "discard"
        elif self in player.deck:
            player.deck.remove(self)
            origin = "deck"
        elif self in player.hand:
            player.hand.remove(self)
            origin = "hand"
        elif self in game_state.trash:
            game_state.trash.remove(self)
            origin = "trash"
        elif self in player.in_play:
            player.in_play.remove(self)
            origin = "in_play"
        else:
            return

        if self.is_action:
            player.actions_played += 1
            player.actions_this_turn += 1

        player.in_play.append(self)
        self.on_play(game_state)

        if origin == "trash":
            if self in player.in_play:
                player.in_play.remove(self)
            if self not in game_state.trash:
                game_state.trash.append(self)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        self.maybe_play_on_reaction(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        self.maybe_play_on_reaction(game_state, player)

    def maybe_play_on_reaction(self, game_state, player):
        """Ask the AI if Trail should be played due to a reaction trigger."""

        choice = player.ai.choose_action(game_state, [self, None])
        if choice is self:
            self._play_now(game_state, player)

    def react_to_discard(self, game_state, player):
        """Handle the discard trigger outside of clean-up."""

        self.maybe_play_on_reaction(game_state, player)
