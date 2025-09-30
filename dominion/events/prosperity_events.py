"""Prosperity second edition events."""

from dominion.cards.base_card import CardCost
from .base_event import Event


class Investment(Event):
    """Trash a card; gain coins or victory tokens based on Treasures."""

    def __init__(self):
        super().__init__("Investment", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return

        card = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if card is None or card not in player.hand:
            return

        player.hand.remove(card)
        game_state.trash_card(player, card)

        distinct_treasures = {c.name for c in player.hand if c.is_treasure}
        if len(distinct_treasures) >= 3:
            player.vp_tokens += len(distinct_treasures)
        else:
            player.coins += 2
