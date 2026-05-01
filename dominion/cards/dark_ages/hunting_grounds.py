from ..base_card import Card, CardCost, CardStats, CardType


class HuntingGrounds(Card):
    """+4 Cards. When trashed, gain a Duchy or 3 Estates."""

    def __init__(self):
        super().__init__(
            name="Hunting Grounds",
            cost=CardCost(coins=6),
            stats=CardStats(cards=4),
            types=[CardType.ACTION],
        )

    def on_trash(self, game_state, player):
        from ..registry import get_card

        choice = player.ai.choose_hunting_grounds_reward(game_state, player)

        duchy_available = game_state.supply.get("Duchy", 0) > 0
        estates_available = game_state.supply.get("Estate", 0) > 0

        if choice == "duchy" and not duchy_available and estates_available:
            choice = "estates"
        if choice == "estates" and not estates_available and duchy_available:
            choice = "duchy"

        if choice == "duchy":
            if duchy_available:
                game_state.supply["Duchy"] -= 1
                game_state.gain_card(player, get_card("Duchy"))
            return

        for _ in range(3):
            if game_state.supply.get("Estate", 0) <= 0:
                break
            game_state.supply["Estate"] -= 1
            game_state.gain_card(player, get_card("Estate"))
