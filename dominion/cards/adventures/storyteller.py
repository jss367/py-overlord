"""Storyteller (Adventures) — $5 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Storyteller(Card):
    def __init__(self):
        super().__init__(
            name="Storyteller",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # Play up to 3 Treasures from hand.
        treasures_in_hand = [c for c in player.hand if c.is_treasure]
        picks = player.ai.choose_treasures_to_play_for_storyteller(
            game_state, player, treasures_in_hand
        )
        coins_before = player.coins
        for card in picks[:3]:
            if card not in player.hand:
                continue
            player.hand.remove(card)
            player.in_play.append(card)
            card.on_play(game_state)
        # Pay all your $.
        coins_to_spend = player.coins
        player.coins = 0
        # +1 Card per $1 paid.
        if coins_to_spend > 0:
            game_state.draw_cards(player, coins_to_spend)
