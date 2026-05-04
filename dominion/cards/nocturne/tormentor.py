"""Tormentor — $5 Action-Attack.

+$2. If no cards in play, gain an Imp; otherwise each other player receives a Hex.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Tormentor(Card):
    nocturne_piles = {"Imp": 13}

    def __init__(self):
        super().__init__(
            name="Tormentor",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.DOOM],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        # "No cards in play" — Tormentor itself was just played and is in
        # play. Per official rules, "while you have nothing else in play"
        # means in_play has just this card.
        others_in_play = [c for c in player.in_play if c is not self]
        if not others_in_play:
            if game_state.supply.get("Imp", 0) > 0:
                game_state.supply["Imp"] -= 1
                game_state.gain_card(player, get_card("Imp"))
        else:
            for other in game_state.players:
                if other is player:
                    continue

                def attack(target):
                    game_state.give_hex_to_player(target)

                game_state.attack_player(other, attack, attacker=player, attack_card=self)
