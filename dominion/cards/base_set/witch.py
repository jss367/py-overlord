from ..base_card import Card, CardCost, CardStats, CardType


class Witch(Card):
    def __init__(self):
        super().__init__(
            name="Witch",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        """Each other player gains a Curse."""
        current_player = game_state.current_player

        def curse_target(target):
            if game_state.supply.get("Curse", 0) > 0:
                game_state.give_curse_to_player(target)
                target_name = (
                    game_state.logger.format_player_name(target.ai.name)
                    if game_state.logger
                    else target.ai.name
                )
                game_state.log_callback(
                    (
                        "action",
                        current_player.ai.name,
                        f"gives curse to {target_name}",
                        {"curses_remaining": game_state.supply.get("Curse", 0)},
                    )
                )

        for player in game_state.players:
            if player != current_player:
                game_state.attack_player(player, curse_target)
