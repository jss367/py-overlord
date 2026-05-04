"""Implementation of the Footpad card from Nocturne.

The card is officially Night-Attack: +2 Coffers, each other player discards
down to 3 cards in hand. The codebase has no Night phase, so Footpad is
modeled as Action-Attack here. Coffers are tracked via the existing
``coin_tokens`` field, which auto-spends like Coffers during the buy phase.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Footpad(Card):
    def __init__(self):
        super().__init__(
            name="Footpad",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.coin_tokens += 2

        def attack_target(target):
            if len(target.hand) <= 3:
                return

            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="footpad"
            )

            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

            while len(target.hand) > 3:
                card = target.hand[-1]
                target.hand.remove(card)
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
