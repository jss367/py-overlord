"""Relic (Adventures) — $5 Treasure-Attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Relic(Card):
    def __init__(self):
        super().__init__(
            name="Relic",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.TREASURE, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            target.minus_card_tokens += 1

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attacker=player, attack_card=self)
