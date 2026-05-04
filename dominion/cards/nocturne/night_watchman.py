"""Night Watchman — $3 Night.

Look at top 5 cards. Discard or put back any in any order.
When you gain this, you may play it.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class NightWatchman(Card):
    def __init__(self):
        super().__init__(
            name="Night Watchman",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.NIGHT],
        )

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if player.ai.should_play_night_watchman_now(game_state, player):
            # Play it from wherever it is now
            if self in player.discard:
                player.discard.remove(self)
            elif self in player.deck:
                player.deck.remove(self)
            elif self in player.hand:
                player.hand.remove(self)
            else:
                return
            player.in_play.append(self)
            self.on_play(game_state)

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed: list = []
        for _ in range(5):
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        if not revealed:
            return
        discard, keep_ordered = player.ai.choose_cards_to_topdeck_or_discard(
            game_state, player, list(revealed)
        )
        # Validate
        keep = [c for c in revealed if c not in discard]
        if not keep_ordered or len(keep_ordered) != len(keep):
            keep_ordered = sorted(keep, key=lambda c: (c.cost.coins, c.name))
        for card in discard:
            game_state.discard_card(player, card)
        for card in keep_ordered:
            player.deck.append(card)
