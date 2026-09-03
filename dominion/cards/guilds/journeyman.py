from ..base_card import Card, CardCost, CardStats, CardType


class Journeyman(Card):
    """Name a card; reveal cards until 3 non-named ones, put them in hand.

    Terminal: the printed card gives no +Action.
    """

    def __init__(self):
        super().__init__(
            name="Journeyman",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        target_name = self._choose_name(player)

        # Keep named cards out of the discard pile until revealing is done.
        # Otherwise, when fewer than three non-named cards remain, the named
        # cards are reshuffled and revealed forever.
        named_cards = []
        drawn = 0
        while drawn < 3:
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            card = player.deck.pop()
            if card.name == target_name:
                named_cards.append(card)
            else:
                player.hand.append(card)
                drawn += 1

        game_state.discard_cards(player, named_cards)

    def _choose_name(self, player) -> str:
        if player.count_in_deck("Curse"):
            return "Curse"
        for candidate in ("Estate", "Overgrown Estate", "Hovel"):
            if player.count_in_deck(candidate):
                return candidate
        if player.count_in_deck("Copper"):
            return "Copper"
        return "Estate"
