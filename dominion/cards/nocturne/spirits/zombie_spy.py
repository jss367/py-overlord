"""Zombie Spy — non-supply Action, $3."""

from ...base_card import Card, CardCost, CardStats, CardType


class ZombieSpy(Card):
    """+1 Card +1 Action. Reveal top of deck, may discard."""

    def __init__(self):
        super().__init__(
            name="Zombie Spy",
            cost=CardCost(coins=3),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.ZOMBIE],
        )

    def starting_supply(self, game_state) -> int:
        return 1

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.deck:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return
        top = player.deck[-1]
        # Discard junky cards
        if top.is_victory or top.name == "Curse" or top.name == "Copper":
            player.deck.pop()
            game_state.discard_card(player, top)
