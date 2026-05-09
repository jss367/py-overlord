from ..base_card import Card, CardCost, CardStats, CardType


class Marchland(Card):
    """Promo Victory-Action ($5):

    +1 Buy. Discard any number of cards for +$1 each.
    Worth 1 VP per 3 Victory cards in your deck (round down).
    """

    def __init__(self):
        super().__init__(
            name="Marchland",
            cost=CardCost(coins=5),
            stats=CardStats(buys=1),
            types=[CardType.ACTION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choices = player.ai.choose_cards_to_discard(
            game_state, player, list(player.hand), len(player.hand), reason="marchland"
        )
        discarded = 0
        for card in choices:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)
                discarded += 1
        player.coins += discarded

    def get_victory_points(self, player) -> int:
        victory_cards = sum(1 for card in player.all_cards() if card.is_victory)
        return victory_cards // 3
