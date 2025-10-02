from ..base_card import Card, CardCost, CardStats, CardType


class Herald(Card):
    """Cantrip that plays the top card of the deck if it's an Action."""

    def __init__(self):
        super().__init__(
            name="Herald",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if not player.deck:
            return

        card = player.deck.pop()
        if card.is_action:
            player.in_play.append(card)
            card.on_play(game_state)
        else:
            game_state.discard_card(player, card)
