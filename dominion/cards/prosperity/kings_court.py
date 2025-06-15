from ..base_card import Card, CardCost, CardStats, CardType


class KingsCourt(Card):
    def __init__(self):
        super().__init__(
            name="King's Court",
            cost=CardCost(coins=7),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return

        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None:
            choice = actions_in_hand[0]

        player.hand.remove(choice)
        player.in_play.append(choice)

        for _ in range(3):
            choice.on_play(game_state)
