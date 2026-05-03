"""Frigate from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Frigate(Card):
    """$5 Action-Duration-Attack: +$3. Each other player discards down to 4 in
    hand now and at the start of your next turn.
    """

    def __init__(self):
        super().__init__(
            name="Frigate",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        self._attack_others(game_state, player)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._attack_others(game_state, player)
        self.duration_persistent = False

    @staticmethod
    def _attack_others(game_state, attacker):
        def discard_to_four(target):
            if len(target.hand) <= 4:
                return

            discard_count = len(target.hand) - 4
            choices = list(target.hand)
            selected = target.ai.choose_cards_to_discard(
                game_state,
                target,
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
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

        for other in game_state.players:
            if other is attacker:
                continue
            game_state.attack_player(other, discard_to_four)
