"""Cage from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Cage(Card):
    """$2 Treasure-Duration: Set aside up to 4 cards from your hand on this.
    At the start of your next turn, if you have 5 cards in hand, take the
    set-aside cards into your hand. Trash this if it has no set-aside cards
    after that.
    """

    def __init__(self):
        super().__init__(
            name="Cage",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player

        for _ in range(4):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_set_aside(
                game_state, player, list(player.hand) + [None], reason="cage"
            )
            if choice is None or choice not in player.hand:
                break
            player.hand.remove(choice)
            self.set_aside.append(choice)

        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player

        if len(player.hand) >= 5 and self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []

        if not self.set_aside:
            if self in player.duration:
                player.duration.remove(self)
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash_card(player, self)
            self.duration_persistent = True
        else:
            self.duration_persistent = True
