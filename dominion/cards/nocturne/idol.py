"""Idol — $5 Treasure-Attack.

If odd # of Idols in play, +$2 and receive a Boon. If even, each other
player gains a Curse.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Idol(Card):
    uses_boons = True

    def __init__(self):
        super().__init__(
            name="Idol",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.ATTACK, CardType.FATE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        idols_in_play = sum(1 for c in player.in_play if c.name == "Idol")
        if idols_in_play % 2 == 1:
            # Odd: +$2 and Boon
            player.coins += 2
            game_state.receive_boon(player)
        else:
            # Even: each other player gains a Curse
            from ..registry import get_card

            for other in game_state.players:
                if other is player:
                    continue

                def attack(target):
                    if game_state.supply.get("Curse", 0) > 0:
                        game_state.give_curse_to_player(target)

                game_state.attack_player(other, attack, attacker=player, attack_card=self)
