from ..base_card import Card, CardCost, CardStats, CardType


class Investment(Card):
    """Treasure ($4): Trash a card from your hand. Choose one: +$1; or trash
    this, reveal your hand, and +1 VP per differently named Treasure in it.
    """

    def __init__(self):
        super().__init__(
            name="Investment",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.hand:
            choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
            if choice is None or choice not in player.hand:
                choice = min(
                    player.hand,
                    key=lambda c: (
                        game_state.is_action(c),
                        game_state.is_treasure(c),
                        c.cost.coins,
                        c.name,
                    ),
                )

            player.hand.remove(choice)
            game_state.trash_card(player, choice)

        can_trash_this = self in player.in_play

        mode = player.ai.choose_investment_mode(
            game_state, player, can_trash_this
        )

        if mode == "trash" and can_trash_this:
            player.in_play.remove(self)
            game_state.trash_card(player, self)

            from ..gain_decisions import live_treasures
            player.vp_tokens += len({c.name for c in live_treasures(game_state, player, player.hand)})
            return

        player.coins += 1
