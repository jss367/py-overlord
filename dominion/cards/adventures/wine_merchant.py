"""Wine Merchant (Adventures) — $5 Action-Reserve."""

from ..base_card import Card, CardCost, CardStats, CardType


class WineMerchant(Card):
    def __init__(self):
        super().__init__(
            name="Wine Merchant",
            cost=CardCost(coins=5),
            stats=CardStats(buys=1, coins=4),
            types=[CardType.ACTION, CardType.RESERVE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        game_state.set_aside_on_tavern(player, self)

    def on_call_from_tavern(self, game_state, player, trigger, *args, **kwargs):
        # Wine Merchant calls itself off the mat in cleanup if you have $2+
        # unspent. We model cleanup_start as the trigger.
        if trigger != "cleanup_start":
            return False
        if (player.coins + player.coin_tokens) < 2:
            return False
        # Move from tavern to discard (no further effect).
        game_state.call_from_tavern(player, self)
        return True
