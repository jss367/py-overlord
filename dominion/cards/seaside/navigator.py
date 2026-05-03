from ..base_card import Card, CardCost, CardStats, CardType


class Navigator(Card):
    """Action ($4): +$2. Look at the top 5 cards of your deck. Either discard them all,
    or put them back on top of your deck in any order.
    """

    def __init__(self):
        super().__init__(
            name="Navigator",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        revealed = []
        for _ in range(5):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        # Heuristic: discard if the top 5 are mostly junk; otherwise put back.
        junk_count = sum(
            1
            for c in revealed
            if c.name == "Curse"
            or c.name == "Copper"
            or (c.is_victory and not c.is_action)
        )

        if junk_count >= 3:
            for card in revealed:
                game_state.discard_card(player, card)
        else:
            ordered = player.ai.order_cards_for_topdeck(game_state, player, revealed)
            # Put back so that the first item in `ordered` ends up on top of deck.
            # In this codebase deck.pop() draws from the end, so "top" == end.
            for card in ordered:
                player.deck.append(card)
