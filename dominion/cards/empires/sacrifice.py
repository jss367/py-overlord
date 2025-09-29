from ..base_card import Card, CardCost, CardStats, CardType


class Sacrifice(Card):
    def __init__(self):
        super().__init__(
            name="Sacrifice",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if to_trash is None:
            to_trash = player.hand[0]
        if to_trash in player.hand:
            player.hand.remove(to_trash)
            game_state.trash_card(player, to_trash)
            if to_trash.is_action:
                game_state.draw_cards(player, 2)
                player.actions += 2
            if to_trash.is_treasure:
                player.coins += 2
            if to_trash.is_victory:
                player.vp_tokens += 2
