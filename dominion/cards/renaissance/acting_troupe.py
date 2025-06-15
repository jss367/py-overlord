from ..base_card import Card, CardCost, CardStats, CardType


class ActingTroupe(Card):
    def __init__(self):
        super().__init__(
            name="Acting Troupe",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.villagers += 4
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                "gains 4 Villagers",
                {"villagers_total": player.villagers},
            )
        )

        if self in player.in_play:
            player.in_play.remove(self)
        game_state.trash_card(player, self)
