from ..base_card import Card, CardCost, CardStats, CardType


class Clerk(Card):
    """Action-Attack-Duration ($4): +$2. Each other player with 5 or more
    cards in hand puts one of them onto their deck. At the start of your
    next turn, you may play this.
    """

    def __init__(self):
        super().__init__(
            name="Clerk",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DURATION],
        )
        self.duration_persistent = False
        # Tracks whether this play is a "may play again" start-of-turn replay.
        self._replaying = False

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) < 5:
                return
            choice = target.ai.choose_card_to_topdeck_for_clerk(
                game_state, target, list(target.hand)
            )
            if choice is None or choice not in target.hand:
                choice = min(
                    target.hand,
                    key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
                )
            target.hand.remove(choice)
            target.deck.append(choice)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

        if not self._replaying:
            # Set up the duration trigger so we may replay next turn.
            if self in player.in_play:
                player.in_play.remove(self)
            if self not in player.duration:
                player.duration.append(self)
            self.duration_persistent = True

    def on_duration(self, game_state):
        """At the start of the next turn the player may play this again.

        After the replay the engine moves us from duration to discard
        because we set ``duration_persistent`` back to False here.
        """

        player = game_state.current_player

        if player.ai.should_replay_clerk(game_state, player):
            self._replaying = True
            try:
                # Resolve the on-play effects again ($2 + attack), but don't
                # re-queue another duration trigger.
                self.on_play(game_state)
                game_state.fire_ally_play_hooks(player, self)
            finally:
                self._replaying = False

        # The engine will discard us once duration_persistent is False.
        self.duration_persistent = False
