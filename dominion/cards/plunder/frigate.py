"""Frigate from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Frigate(Card):
    """$5 Action-Duration-Attack.

    +$3. Until your next turn, each time another player plays an Action card,
    they discard down to 4 cards in hand.
    """

    def __init__(self):
        super().__init__(
            name="Frigate",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True
        self._owner = None
        self._active = False

    def play_effect(self, game_state):
        player = game_state.current_player
        self._owner = player
        self._active = True
        player.duration.append(self)

    def on_duration(self, game_state):
        # Frigate's effect ends at the start of the owner's next turn.
        self._active = False
        self.duration_persistent = False

    def on_action_played(self, game_state, owner, action_player, action_card):
        """Called whenever any player plays an Action card. If Frigate is
        active and the player is not its owner, force them to discard down
        to 4.
        """

        if not self._active:
            return
        if owner is not self._owner:
            return
        if action_player is self._owner:
            return

        if len(action_player.hand) <= 4:
            return

        discard_count = len(action_player.hand) - 4
        choices = list(action_player.hand)
        selected = action_player.ai.choose_cards_to_discard(
            game_state,
            action_player,
            choices,
            discard_count,
            reason="frigate",
        )

        remaining = list(choices)
        picked = []
        for card in selected:
            if card in remaining:
                remaining.remove(card)
                picked.append(card)
        while len(picked) < discard_count and remaining:
            picked.append(remaining.pop(0))

        for card in picked:
            if card in action_player.hand:
                action_player.hand.remove(card)
                game_state.discard_card(action_player, card)

    def on_discard_from_play(self, game_state, player):
        self._active = False
        self._owner = None
