"""King's Cache from the Plunder expansion."""

from ..base_card import Card, CardCost, CardStats, CardType


class KingsCache(Card):
    """$7 Treasure: +$3. When you play this, you may play a Treasure from your
    hand 3 times.
    """

    def __init__(self):
        super().__init__(
            name="King's Cache",
            cost=CardCost(coins=7),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        treasures = [c for c in player.hand if c.is_treasure]
        if not treasures:
            return

        choice = player.ai.choose_treasure(game_state, list(treasures) + [None])
        if choice is None or choice not in player.hand:
            return

        player.hand.remove(choice)
        player.in_play.append(choice)

        for _ in range(3):
            choice.on_play(game_state)
