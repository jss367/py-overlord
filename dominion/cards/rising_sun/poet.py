from ..base_card import Card, CardCost, CardStats, CardType


class Poet(Card):
    """Action-Omen ($4): +1 Sun, +1 Card, +1 Action.
    Reveal the top card of your deck. If it costs up to $3, put it into your
    hand. Otherwise, put it back on top of your deck.
    """

    def __init__(self):
        super().__init__(
            name="Poet",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.OMEN],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        top_card = player.deck[-1]
        cost = game_state.get_card_cost(player, top_card)
        # "Up to $3" excludes cards with debt in the cost.
        if top_card.cost.debt > 0 or cost > 3:
            return  # leave on top
        player.deck.pop()
        player.hand.append(top_card)
