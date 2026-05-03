from ..base_card import Card, CardCost, CardStats, CardType


class MountainShrine(Card):
    """Action-Omen ($5 Debt): +1 Sun, +$2.
    You may trash a card from your hand. Then if there are any Action cards
    in the trash, +2 Cards.

    Cost is pure Debt — buying it gives you 5 Debt. (Per the rulebook, "up
    to $X" exclusions skip cards with any Debt in their cost.)
    """

    def __init__(self):
        super().__init__(
            name="Mountain Shrine",
            cost=CardCost(coins=0, debt=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.OMEN],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.hand:
            trash_choice = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if trash_choice is not None and trash_choice in player.hand:
                player.hand.remove(trash_choice)
                game_state.trash_card(player, trash_choice)

        if any(c.is_action for c in game_state.trash):
            game_state.draw_cards(player, 2)
