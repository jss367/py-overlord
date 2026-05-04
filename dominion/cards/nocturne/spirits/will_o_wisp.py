"""Will-o'-Wisp — non-supply Action-Spirit, $0."""

from ...base_card import Card, CardCost, CardStats, CardType


class WillOWisp(Card):
    """+1 Card +1 Action. Reveal top of deck. If costs $2 or less, +1 Card."""

    def __init__(self):
        super().__init__(
            name="Will-o'-Wisp",
            cost=CardCost(coins=0),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.SPIRIT],
        )

    def starting_supply(self, game_state) -> int:
        return 12

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        top = player.deck[-1]
        # Reveal — keep on top of deck regardless.
        if top.cost.coins <= 2 and top.cost.potions == 0 and top.cost.debt == 0:
            game_state.draw_cards(player, 1)
