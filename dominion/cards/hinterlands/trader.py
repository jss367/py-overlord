from ..base_card import Card, CardCost, CardStats, CardType


def _gain_silver(game_state, player):
    """Gain a Silver for ``player`` if any remain in the supply."""

    from ..registry import get_card

    if game_state.supply.get("Silver", 0) <= 0:
        return False

    silver = get_card("Silver")
    game_state.supply["Silver"] -= 1
    game_state.gain_card(player, silver)
    return True


class Trader(Card):
    def __init__(self):
        super().__init__(
            name="Trader",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.hand:
            return

        selections = player.ai.choose_cards_to_trash(game_state, list(player.hand), 1)
        card_to_trash = selections[0] if selections else None

        if not card_to_trash:
            return

        cost_in_coins = game_state.get_card_cost(player, card_to_trash)
        player.hand.remove(card_to_trash)
        game_state.trash_card(player, card_to_trash)

        # Gain Silvers equal to the trashed card's coin cost.
        for _ in range(cost_in_coins):
            if not _gain_silver(game_state, player):
                break
