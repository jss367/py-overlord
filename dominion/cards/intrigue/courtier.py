"""Implementation of Courtier."""

from ..base_card import Card, CardCost, CardStats, CardType


class Courtier(Card):
    """Reveal a card from your hand. For each type it has, choose one:
    +1 Action; +1 Buy; +$3; gain a Gold. The choices must be different."""

    def __init__(self):
        super().__init__(
            name="Courtier",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        revealed = player.ai.choose_courtier_reveal(
            game_state, player, list(player.hand)
        )
        if revealed is None or revealed not in player.hand:
            return

        # Number of types on the revealed card determines bonuses.
        num_types = len(revealed.types)
        # The four available options:
        options = ["action", "buy", "coins", "gold"]
        choices = player.ai.choose_courtier_options(
            game_state, player, list(options), min(num_types, len(options))
        )

        # Deduplicate while preserving order, and cap at num_types.
        seen = set()
        ordered: list[str] = []
        for c in choices:
            if c in options and c not in seen:
                ordered.append(c)
                seen.add(c)
            if len(ordered) == min(num_types, len(options)):
                break

        # If AI returned fewer than required, fill in with default priority.
        priority = ["coins", "gold", "action", "buy"]
        for opt in priority:
            if len(ordered) >= min(num_types, len(options)):
                break
            if opt not in seen:
                ordered.append(opt)
                seen.add(opt)

        for choice in ordered:
            if choice == "action":
                player.actions += 1
            elif choice == "buy":
                player.buys += 1
            elif choice == "coins":
                player.coins += 3
            elif choice == "gold":
                if game_state.supply.get("Gold", 0) > 0:
                    game_state.supply["Gold"] -= 1
                    game_state.log_callback(
                        ("supply_change", "Gold", -1, game_state.supply["Gold"])
                    )
                    game_state.gain_card(player, get_card("Gold"))
