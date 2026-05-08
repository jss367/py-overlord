"""Apprentice - Action from Alchemy."""

from ..base_card import Card, CardCost, CardStats, CardType


class Apprentice(Card):
    """Action ($5): +1 Action. Trash a card from your hand.
    +1 Card per $1 it costs. +2 Cards if it has 1+ Potions in its cost.
    """

    def __init__(self):
        super().__init__(
            name="Apprentice",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        target = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if target is None or target not in player.hand:
            return
        cards_to_draw = target.cost.coins + (2 if target.cost.potions > 0 else 0)
        player.hand.remove(target)
        game_state.trash_card(player, target)
        if cards_to_draw > 0:
            game_state.draw_cards(player, cards_to_draw)
