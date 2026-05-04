"""Implementation of Minion."""

from ..base_card import Card, CardCost, CardStats, CardType


class Minion(Card):
    """+1 Action. Choose one: +$2; or discard your hand, +4 Cards, and each
    other player with 5 or more cards in hand discards their hand and
    draws 4."""

    def __init__(self):
        super().__init__(
            name="Minion",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        mode = player.ai.choose_minion_mode(game_state, player)
        if mode == "coins":
            player.coins += 2
            return

        # mode == "discard"
        # Discard own hand and draw 4.
        if player.hand:
            old_hand = list(player.hand)
            player.hand = []
            game_state.discard_cards(player, old_hand)
        game_state.draw_cards(player, 4)

        # Each other player with 5+ in hand discards and draws 4 (this is
        # an Attack, so block-by-Moat etc applies).
        def attack_target(target):
            if len(target.hand) < 5:
                return
            old = list(target.hand)
            target.hand = []
            game_state.discard_cards(target, old)
            game_state.draw_cards(target, 4)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
