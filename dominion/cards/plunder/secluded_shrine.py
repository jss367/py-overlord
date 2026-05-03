"""Secluded Shrine from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class SecludedShrine(Card):
    """$3 Action-Duration: +1 Action. At start of next turn, may trash up to 2 cards from hand."""

    def __init__(self):
        super().__init__(
            name="Secluded Shrine",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player

        for _ in range(2):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if choice is None or choice not in player.hand:
                break
            player.hand.remove(choice)
            game_state.trash_card(player, choice)

        self.duration_persistent = False
