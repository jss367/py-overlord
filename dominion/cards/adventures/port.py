"""Port (Adventures) — $4 Action."""

from ..base_card import Card, CardCost, CardStats, CardType


class Port(Card):
    def __init__(self):
        super().__init__(
            name="Port",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )
        # Internal flag so the bonus copy doesn't recurse and gain another
        # Port itself. Set on the bonus instance before it is gained.
        self._is_port_bonus_copy = False

    def starting_supply(self, game_state) -> int:
        return 12

    def on_gain(self, game_state, player):
        # Run the base on_gain first (it tracks gained-this-turn bookkeeping).
        super().on_gain(game_state, player)
        # When you gain this, also gain a second Port from the supply.
        # Port's text is "When you gain this, also gain a Port", so the
        # trigger is on GAIN (not just on buy) — this fires for Workshop /
        # Ironworks / Inheritance-via-Estate / Trader / etc.
        if getattr(self, "_is_port_bonus_copy", False):
            # Don't recurse: the bonus copy itself does NOT gain another Port.
            return
        if game_state.supply.get("Port", 0) <= 0:
            return
        from ..registry import get_card

        bonus = get_card("Port")
        bonus._is_port_bonus_copy = True
        game_state.supply["Port"] -= 1
        game_state.gain_card(player, bonus)
