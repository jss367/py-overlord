"""Ghost — non-supply Action-Night-Duration-Spirit, $4."""

from ...base_card import Card, CardCost, CardStats, CardType


class Ghost(Card):
    """Reveal cards until you reveal an Action.

    Set it aside, discard the rest. At the start of each of the next two
    turns, play that Action.
    """

    def __init__(self):
        super().__init__(
            name="Ghost",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.NIGHT, CardType.DURATION, CardType.SPIRIT],
        )

    def starting_supply(self, game_state) -> int:
        return 6

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []
        action_card = None
        while True:
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            top = player.deck.pop()
            if top.is_action:
                action_card = top
                break
            revealed.append(top)
        for card in revealed:
            game_state.discard_card(player, card)
        if action_card is None:
            return
        # Schedule two plays at the start of the next two turns.
        player.ghost_pending_actions.append((action_card, 2))
        # Persist Ghost in duration so it sticks until plays complete.
        self.duration_persistent = True
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        # No additional effect — Ghost's plays are scheduled via the player's
        # ghost_pending_actions list (handled at start of turn). Stay in
        # play while plays remain.
        player = game_state.current_player
        any_pending = any(plays > 0 for _, plays in player.ghost_pending_actions)
        self.duration_persistent = any_pending
