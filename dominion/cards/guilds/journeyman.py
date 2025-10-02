from ..base_card import Card, CardCost, CardStats, CardType


class Journeyman(Card):
    """Reveals until three non-named cards are drawn."""

    def __init__(self):
        super().__init__(
            name="Journeyman",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        target_name = self._choose_name(player)

        drawn = 0
        while drawn < 3 and (player.deck or player.discard):
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            card = player.deck.pop()
            if card.name == target_name:
                game_state.discard_card(player, card)
            else:
                player.hand.append(card)
                drawn += 1

    def _choose_name(self, player) -> str:
        if player.count_in_deck("Curse"):
            return "Curse"
        for candidate in ("Estate", "Overgrown Estate", "Hovel"):
            if player.count_in_deck(candidate):
                return candidate
        if player.count_in_deck("Copper"):
            return "Copper"
        return "Estate"
