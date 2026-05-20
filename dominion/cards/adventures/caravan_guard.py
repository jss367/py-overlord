"""Caravan Guard (Adventures) — $3 Action-Duration-Reaction."""

from ..base_card import Card, CardCost, CardStats, CardType


class CaravanGuard(Card):
    def __init__(self):
        super().__init__(
            name="Caravan Guard",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.DURATION, CardType.REACTION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        self.duration_persistent = False

    def react_to_attack(self, game_state, player, attacker, attack_card) -> bool:
        # Caravan Guard plays itself when an opponent plays an Attack. It
        # doesn't block the attack — it just gets played. Implementation:
        # remove from hand, run play_effect, but DO NOT consume an Action.
        if self not in player.hand:
            return False
        game_state.play_action_from_hand_indirectly(player, self)
        # Caravan Guard does NOT block the attack itself.
        return False
