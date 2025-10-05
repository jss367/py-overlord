from ..base_card import Card, CardCost, CardStats, CardType


class Archive(Card):
    """Simplified implementation of Archive as a duration draw card."""

    def __init__(self):
        super().__init__(
            name="Archive",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.set_aside: list = []
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        self.set_aside = []

        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            self.set_aside.append(player.deck.pop())

        self.duration_persistent = bool(self.set_aside)
        if self.set_aside:
            player.duration.append(self)
        else:
            self.duration_persistent = False

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            choice = player.ai.choose_archive_card(
                game_state, player, list(self.set_aside)
            )
            if choice not in self.set_aside:
                choice = self.set_aside[0]

            self.set_aside.remove(choice)
            player.hand.append(choice)

        if not self.set_aside:
            self.duration_persistent = False
