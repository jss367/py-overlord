"""Ghost — non-supply Night-Duration-Spirit, $4."""

from ...base_card import Card, CardCost, CardStats, CardType


class Ghost(Card):
    """Reveal cards until you reveal an Action.

    Set it aside, discard the rest. At the start of your next turn,
    play that Action twice.
    """

    def __init__(self):
        super().__init__(
            name="Ghost",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.NIGHT, CardType.DURATION, CardType.SPIRIT],
        )

        self.set_aside = []

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
        self.set_aside.append(action_card)
        self.duration_persistent = True
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        from ...allies._rules import retain_multiplier

        player = game_state.current_player
        actions = list(self.set_aside)
        self.set_aside.clear()
        self.duration_persistent = False
        for action in actions:
            player.in_play.append(action)
            for _ in range(2):
                game_state.play_action_indirectly(player, action)
            retain_multiplier(player, self, action)
