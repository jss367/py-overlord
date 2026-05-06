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
        player.hand.remove(self)
        player.in_play.append(self)
        # Skip cardstats (already supposed to take +1 Card +1 Action).
        # Mirror Card.on_play but bypass remove_sun_token (this isn't an Omen)
        # and don't apply ignore_action_bonuses since reactions are exempt.
        player.actions += self.stats.actions
        player.coins += self.stats.coins
        player.buys += self.stats.buys
        if self.stats.cards > 0:
            game_state.draw_cards(player, self.stats.cards)
        # Move to duration so on_duration triggers next turn.
        if self in player.in_play:
            player.in_play.remove(self)
        player.duration.append(self)
        self.duration_persistent = True
        # Caravan Guard does NOT block the attack itself.
        return False
