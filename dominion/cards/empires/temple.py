from ..base_card import Card, CardCost, CardStats, CardType


class Temple(Card):
    def __init__(self):
        super().__init__(
            name="Temple",
            cost=CardCost(coins=4),
            stats=CardStats(vp=1),
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
            game_state.temple_pile_tokens += trashed
            if game_state.temple_pile_tokens >= 3:
                player.vp_tokens += game_state.temple_pile_tokens
                game_state.temple_pile_tokens = 0
                if self in player.in_play:
                    player.in_play.remove(self)
                game_state.trash_card(player, self)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.temple_pile_tokens:
            player.vp_tokens += game_state.temple_pile_tokens
            game_state.temple_pile_tokens = 0
