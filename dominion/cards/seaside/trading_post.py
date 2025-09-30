"""Implementation of the Trading Post trasher."""

from ..base_card import Card, CardCost, CardStats, CardType


class TradingPost(Card):
    def __init__(self):
        super().__init__(
            name="Trading Post",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.hand) < 2:
            return

        choices = player.ai.choose_cards_to_trash(game_state, list(player.hand), 2)
        while len(choices) < 2 and player.hand:
            fallback = min(player.hand, key=lambda c: (c.cost.coins, c.name))
            if fallback not in choices:
                choices.append(fallback)

        trashed = 0
        for card in choices[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
                trashed += 1

        if trashed == 2 and game_state.supply.get("Silver", 0) > 0:
            from ..registry import get_card

            silver = get_card("Silver")
            game_state.supply["Silver"] -= 1
            gained = game_state.gain_card(player, silver)
            if gained in player.discard:
                player.discard.remove(gained)
                player.hand.append(gained)
