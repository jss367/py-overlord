"""Familiar - Action - Attack from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Familiar(Card):
    """Action - Attack ($3P): +1 Card, +1 Action.

    Each other player gains a Curse.
    """

    def __init__(self):
        super().__init__(
            name="Familiar",
            cost=CardCost(coins=3, potions=1),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        def curse_target(target):
            if game_state.supply.get("Curse", 0) > 0:
                game_state.give_curse_to_player(target)

        for player in game_state.players:
            if player is attacker:
                continue
            game_state.attack_player(
                player, curse_target, attacker=attacker, attack_card=self
            )
