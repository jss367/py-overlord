from ..base_card import Card, CardCost, CardStats, CardType


class Mill(Card):
    """+1 Card, +1 Action. You may discard 2 cards, for +$2."""

    def __init__(self):
        super().__init__(
            name="Mill",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1, vp=1),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.hand) < 2:
            return

        # The discard is optional and costs two cards for two coins, so it is
        # the player's call, not a fixed rule. A short answer declines.
        chosen = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 2, reason="mill"
        )

        # Mill is two discards or none, so both cards are resolved to distinct
        # cards still in hand before either one leaves it. Discarding first and
        # counting afterwards would spend a card for no coins when a strategy
        # answers with a duplicate or a card it has already played.
        discards = []
        remaining = list(player.hand)
        for card in chosen:
            match = next((c for c in remaining if c is card), None)
            if match is None:
                continue
            remaining.remove(match)
            discards.append(match)
            if len(discards) == 2:
                break
        if len(discards) < 2:
            return

        for card in discards:
            player.hand.remove(card)
            game_state.discard_card(player, card)
        player.coins += 2
