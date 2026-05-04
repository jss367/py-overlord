"""Secret Cave — $3 Action-Duration.

+1 Card +1 Action. You may discard 3 cards. If you do, +$3 next turn.
(Heirloom: Magic Lamp.)
"""

from ..base_card import Card, CardCost, CardStats, CardType


class SecretCave(Card):
    heirloom = "Magic Lamp"

    def __init__(self):
        super().__init__(
            name="Secret Cave",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        # Whether the +$3 next turn fires.
        self._discarded_three = False

    def play_effect(self, game_state):
        player = game_state.current_player
        choice = player.ai.choose_secret_cave_discards(game_state, player)
        if not choice or len(choice) < 3 or len(player.hand) < 3:
            self._discarded_three = False
            return

        actually = []
        for card in choice[:3]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                actually.append(card)
        if len(actually) < 3:
            # Couldn't actually discard 3 — bonus doesn't trigger.
            self._discarded_three = False
            return

        self._discarded_three = True
        if self in player.in_play:
            player.in_play.remove(self)
        if self not in player.duration:
            player.duration.append(self)
        self.duration_persistent = True

    def on_duration(self, game_state):
        player = game_state.current_player
        if self._discarded_three:
            player.coins += 3
        self._discarded_three = False
        self.duration_persistent = False
