from ..base_card import Card, CardCost, CardStats, CardType


class Nobles(Card):
    """Intrigue Nobles implementation with simple choice logic."""

    def __init__(self):
        super().__init__(
            name="Nobles",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        # +2 Actions only helps if (a) we have no remaining actions and
        # (b) there's at least one Action card in hand to play. Otherwise
        # +3 Cards is strictly better (cards may be Actions themselves, but
        # that's already covered by the "actions in hand" check).
        action_cards_in_hand = any(card.is_action for card in player.hand)
        if player.actions == 0 and action_cards_in_hand:
            player.actions += 2
        else:
            game_state.draw_cards(player, 3)
