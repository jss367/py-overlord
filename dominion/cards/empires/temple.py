from ..base_card import Card, CardCost, CardStats, CardType


class Temple(Card):
    def __init__(self):
        super().__init__(
            name="Temple",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        trashed = 0
        for _ in range(2):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
            if choice is None:
                break
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
            trashed += 1
        if trashed:
            player.vp_tokens += trashed
