from ..base_card import Card, CardCost, CardStats, CardType


class WanderingMinstrel(Card):
    """+1 Card, +2 Actions. Reveal the top 3 cards of your deck.

    Put the revealed Actions back on top in any order; discard the rest.
    """

    def __init__(self):
        super().__init__(
            name="Wandering Minstrel",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed: list[Card] = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        actions = [c for c in revealed if c.is_action]
        non_actions = [c for c in revealed if not c.is_action]

        ordered = player.ai.order_cards_for_topdeck(game_state, player, actions)
        # `order_cards_for_topdeck` returns the topdeck order from top to bottom;
        # push them onto the deck in reverse so the first item ends up on top.
        for card in reversed(ordered):
            player.deck.append(card)

        for card in non_actions:
            game_state.discard_card(player, card)
