"""Village Green - Action-Reaction-Duration from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class VillageGreen(Card):
    """You may discard this from hand. If you do, +1 Card +2 Actions.
    When you discard this other than during cleanup: now or at start of next
    turn, +1 Card +2 Actions.
    """

    def __init__(self):
        super().__init__(
            name="Village Green",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION, CardType.DURATION],
        )
        self._pending_next_turn = False

    def play_effect(self, game_state):
        # Played from hand normally → +1 Card +2 Actions delivered now (per the
        # "you may discard this from hand" branch reads as the reaction).
        # When played as an action, you choose to play it normally; we mirror
        # that as: gives the +1 Card +2 Actions immediately. The duration
        # branch is triggered only by discard reactions.
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        player.actions += 2

    def react_to_discard(self, game_state, player) -> None:
        """Triggered when discarded outside cleanup. Player may resolve the
        +1 Card +2 Actions now or at start of next turn.
        """
        choose_now = player.ai.should_play_village_green_now(game_state, player)
        if choose_now:
            game_state.draw_cards(player, 1)
            player.actions += 2
        else:
            # Set aside as duration for next turn
            self._pending_next_turn = True
            if self in player.discard:
                player.discard.remove(self)
            player.duration.append(self)
            self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self._pending_next_turn:
            game_state.draw_cards(player, 1)
            player.actions += 2
            self._pending_next_turn = False
        self.duration_persistent = False
