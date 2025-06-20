from ..base_card import Card, CardCost, CardStats, CardType


class Forager(Card):
    def __init__(self):
        super().__init__(
            name="Forager",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, buys=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        card_to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if card_to_trash is None:
            card_to_trash = player.hand[0]
        player.hand.remove(card_to_trash)
        game_state.trash_card(player, card_to_trash)

        # Count different treasures in trash
        treasure_names = {c.name for c in game_state.trash if c.is_treasure}
        player.coins += len(treasure_names)
