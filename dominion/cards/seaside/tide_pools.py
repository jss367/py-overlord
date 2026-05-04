from ..base_card import Card, CardCost, CardStats, CardType


class TidePools(Card):
    """Action-Duration ($4): +3 Cards, +1 Action. At the start of your next turn,
    discard 2 cards.
    """

    def __init__(self):
        super().__init__(
            name="Tide Pools",
            cost=CardCost(coins=4),
            stats=CardStats(cards=3, actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player

        to_discard = min(2, len(player.hand))
        if to_discard > 0:
            selected = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), to_discard, reason="tide_pools"
            )

            discarded = 0
            for card in selected:
                if discarded >= to_discard:
                    break
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    discarded += 1

            while discarded < to_discard and player.hand:
                card = min(
                    player.hand,
                    key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
                )
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1

        self.duration_persistent = False
