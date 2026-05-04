"""Mercenary — non-supply Action-Attack from Urchin's "trash to gain" effect."""

from ..base_card import Card, CardCost, CardStats, CardType


class Mercenary(Card):
    """You may trash 2 cards from your hand.

    If you do: +2 Cards, +$2, and each other player discards down to 3 cards
    in hand. Mercenary is a non-supply card. It is only gained via Urchin.
    """

    def __init__(self):
        super().__init__(
            name="Mercenary",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def starting_supply(self, game_state) -> int:
        return 0

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player

        if len(player.hand) < 2:
            return

        choices = player.ai.should_play_mercenary_trash(
            game_state, player, list(player.hand)
        )
        valid = [c for c in choices if c in player.hand]
        # Need exactly 2 cards trashed to fire the effect
        if len(valid) < 2:
            return
        valid = valid[:2]
        for card in valid:
            player.hand.remove(card)
            game_state.trash_card(player, card)

        # +2 Cards, +$2
        game_state.draw_cards(player, 2)
        player.coins += 2

        # Each other player discards down to 3
        def discard_down(target):
            while len(target.hand) > 3:
                excess = len(target.hand) - 3
                chosen = target.ai.choose_cards_to_discard(
                    game_state, target, list(target.hand), excess,
                    reason="mercenary",
                )
                if not chosen:
                    chosen = target.hand[:excess]
                discarded = 0
                for card in chosen:
                    if card in target.hand and discarded < excess:
                        target.hand.remove(card)
                        game_state.discard_card(target, card)
                        discarded += 1
                if discarded == 0:
                    break

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, discard_down)
