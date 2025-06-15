from ..base_card import Card, CardCost, CardStats, CardType


class Contraband(Card):
    def __init__(self):
        super().__init__(
            name="Contraband",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        """Next player names a card the current player cannot buy this turn."""
        from ..registry import get_card  # Avoid circular import

        if not game_state.players:
            return

        current_index = game_state.current_player_index
        next_index = (current_index + 1) % len(game_state.players)
        next_player = game_state.players[next_index]

        choices = [get_card(name) for name, count in game_state.supply.items() if count > 0]
        if not choices:
            return

        banned = next_player.ai.choose_buy(game_state, choices)
        if banned is None:
            banned = choices[0]

        game_state.current_player.banned_buys.append(banned.name)
        game_state.log_callback(
            (
                "action",
                next_player.ai.name,
                f"bans {banned.name} with Contraband",
                {},
            )
        )
