"""Dungeon (Adventures) — $3 Action-Duration."""

from ..base_card import Card, CardCost, CardStats, CardType


class Dungeon(Card):
    def __init__(self):
        super().__init__(
            name="Dungeon",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def _draw_then_discard_two(self, game_state, player):
        game_state.draw_cards(player, 2)
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), 2, reason="dungeon"
        )
        actually = 0
        for card in picks[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                actually += 1
        # Card text mandates the second discard: if the AI under-selected,
        # force-discard the cheapest remaining cards until two are gone or
        # the hand is empty.
        while actually < 2 and player.hand:
            fallback = min(player.hand, key=lambda c: (c.cost.coins, c.name))
            player.hand.remove(fallback)
            game_state.discard_card(player, fallback)
            actually += 1

    def play_effect(self, game_state):
        player = game_state.current_player
        self._draw_then_discard_two(game_state, player)
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._draw_then_discard_two(game_state, player)
        self.duration_persistent = False
