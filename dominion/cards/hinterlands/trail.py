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

        # Route through the engine's shared indirect-play helpers so this
        # reaction play gets the same bookkeeping as every other one (owner
        # swap for off-turn plays, Way offer, Warlord/Enchantress, Prophecy,
        # Ally, Tavern, Kiln, Training and Citadel hooks).
        from_trash = self in game_state.trash
        if self in player.in_play:
            game_state.play_action_as_owner_indirectly(player, self)
        else:
            for zone in (player.discard, player.deck, player.hand, game_state.trash):
                if self in zone:
                    game_state.play_action_from_zone_indirectly(player, self, zone)
                    break
            else:
                return

        # A trashed Trail that reacts comes back: "playing it means you get
        # the Trail back; it will go into play, and be discarded into your
        # discard pile in that turn's Clean-up" (official FAQ). The trash
        # itself still happened for whoever caused it (Remodel, Barbarian).
        if from_trash and self in game_state.trash:
            game_state.trash.remove(self)

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
