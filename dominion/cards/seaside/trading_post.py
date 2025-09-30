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
        if not player.hand:
            return

        trash_target = min(2, len(player.hand))
        requested = player.ai.choose_cards_to_trash(
            game_state, list(player.hand), trash_target
        )

        selected: list[Card] = []
        for card in requested:
            if card in player.hand and card not in selected:
                selected.append(card)
            if len(selected) == trash_target:
                break

        while len(selected) < trash_target:
            remaining = [card for card in player.hand if card not in selected]
            if not remaining:
                break
            fallback = min(remaining, key=lambda c: (c.cost.coins, c.name))
            selected.append(fallback)

        trashed = 0
        for card in selected:
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
