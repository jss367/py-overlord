"""Villain: Action-Attack ($5). +2 Coffers.

Each other player with 5+ cards in hand discards a card costing $2 or
more (or reveals they can't).
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Villain(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Villain",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player
        attacker.coin_tokens += 2

        def attack(target):
            if len(target.hand) < 5:
                return
            options = [c for c in target.hand if c.cost.coins >= 2]
            if not options:
                return
            # Target picks (default heuristic via choose_cards_to_discard).
            picks = target.ai.choose_cards_to_discard(
                game_state, target, options, 1, reason="villain"
            )
            chosen = next((c for c in picks if c in target.hand), None)
            if chosen is None:
                # Mandatory — discard cheapest qualifying card.
                chosen = min(options, key=lambda c: (c.cost.coins, c.name))
            if chosen in target.hand:
                target.hand.remove(chosen)
                game_state.discard_card(target, chosen)

        for player in game_state.players:
            if player is attacker:
                continue
            game_state.attack_player(player, attack, attacker=attacker, attack_card=self)
