"""Stowaway from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Stowaway(Card):
    """$3 Action-Duration-Reaction.

    Now and at the start of your next turn: +2 Cards, +1 Action.

    When another player plays an Attack card, you may first set this aside
    from your hand to play it; if you do, return it to your hand at end of
    turn.
    """

    def __init__(self):
        super().__init__(
            name="Stowaway",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.REACTION],
        )
        self.duration_persistent = True
        self._return_to_hand = False

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        player.actions += 1
        self.duration_persistent = False

    def react_to_attack(self, game_state, player):
        if self not in player.hand:
            return None

        if not player.ai.should_react_with_stowaway(game_state, player):
            return None

        game_state.log_callback(
            ("action", player.ai.name, "reacts with Stowaway", {})
        )

        # Reactive plays don't go through the duration cycle: the card
        # returns to the reacting player's hand at end of turn instead.
        player.hand.remove(self)
        player.in_play.append(self)
        self._return_to_hand = True

        game_state.draw_cards(player, 2)
        player.actions += 1
        # Notify cards in play (any player's) that an Action was played, so
        # global hooks (Frigate, Harbor Village, etc.) fire correctly.
        game_state._dispatch_on_action_played(player, self)
        return None  # does not block the attack

    def on_discard_from_play(self, game_state, player):
        if self._return_to_hand:
            self._return_to_hand = False
            return "hand"
        return None
