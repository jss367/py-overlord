from ..base_card import Card, CardCost, CardStats, CardType


class Archive(Card):
    """Each play keeps a separate three-card batch and next-turn instruction."""

    # Individual batches can finish on different turns. The card explicitly
    # requeues only a batch that still has cards, rather than renewing every
    # invocation from one shared persistence flag.
    schedules_own_duration = True

    def __init__(self):
        super().__init__(
            name="Archive",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []
        self.pending_batches: list[list] = []

    def play_effect(self, game_state):
        player = game_state.current_player
        batch = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            batch.append(player.deck.pop())
        self.set_aside.extend(batch)
        self._put_one_into_hand(game_state, batch)
        if batch:
            self.pending_batches.append(batch)
            player.duration.append(self)
        self.duration_persistent = bool(self.pending_batches)

    def on_duration(self, game_state):
        if not self.pending_batches:
            self.duration_persistent = False
            return
        batch = self.pending_batches.pop(0)
        self._put_one_into_hand(game_state, batch)
        if batch:
            self.pending_batches.append(batch)
            game_state.current_player.duration.append(self)
        self.duration_persistent = bool(self.pending_batches)

    def _put_one_into_hand(self, game_state, batch):
        if not batch:
            return
        player = game_state.current_player
        choice = player.ai.choose_archive_card(game_state, player, list(batch))
        if choice not in batch:
            choice = batch[0]
        batch.remove(choice)
        self.set_aside.remove(choice)
        player.hand.append(choice)
