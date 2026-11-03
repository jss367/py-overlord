from ..base_card import Card, CardCost, CardStats, CardType


class Church(Card):
    """Each play stores a batch and offers its own next-turn trash."""

    def __init__(self):
        super().__init__(
            name="Church",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []
        self.pending_batches: list[list] = []

    def play_effect(self, game_state):
        player = game_state.current_player
        selected = player.ai.choose_cards_to_set_aside_for_church(
            game_state, player, list(player.hand), 3
        )
        batch = []
        for card in selected or []:
            if card in player.hand:
                player.hand.remove(card)
                batch.append(card)
            if len(batch) == 3:
                break
        self.set_aside.extend(batch)
        self.pending_batches.append(batch)
        # The optional trash is still pending when no cards were set aside.
        player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if not self.pending_batches:
            self.duration_persistent = False
            return
        batch = self.pending_batches.pop(0)
        for card in batch:
            self.set_aside.remove(card)
            player.hand.append(card)
        to_trash = player.ai.choose_church_trash(game_state, player)
        if to_trash and to_trash in player.hand:
            player.hand.remove(to_trash)
            game_state.trash_card(player, to_trash)
        self.duration_persistent = bool(self.pending_batches)
