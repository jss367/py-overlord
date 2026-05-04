"""Implementation of Baron."""

from ..base_card import Card, CardCost, CardStats, CardType


class Baron(Card):
    """+1 Buy. You may discard an Estate for +$4. Otherwise, gain an Estate."""

    def __init__(self):
        super().__init__(
            name="Baron",
            cost=CardCost(coins=4),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player

        wants_to_discard = player.ai.should_discard_estate_for_baron(
            game_state, player
        )
        estate = next((c for c in player.hand if c.name == "Estate"), None)

        if wants_to_discard and estate is not None:
            player.hand.remove(estate)
            game_state.discard_card(player, estate)
            player.coins += 4
            return

        # Otherwise gain an Estate.
        if game_state.supply.get("Estate", 0) > 0:
            game_state.supply["Estate"] -= 1
            game_state.log_callback(
                ("supply_change", "Estate", -1, game_state.supply["Estate"])
            )
            game_state.gain_card(player, get_card("Estate"))
