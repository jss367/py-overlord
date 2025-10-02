from ..base_card import Card, CardCost, CardStats, CardType


class Doctor(Card):
    """Reveals and trashes junk from the top of the deck."""

    def __init__(self):
        super().__init__(
            name="Doctor",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        name = self._choose_junk_name(player)

        revealed: list = []
        for _ in range(3):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())

        if not revealed:
            return

        to_discard: list = []
        for card in revealed:
            if card.name == name:
                game_state.trash_card(player, card)
            else:
                to_discard.append(card)

        for card in to_discard:
            game_state.discard_card(player, card)

    def _choose_junk_name(self, player) -> str:
        if player.count_in_deck("Curse"):
            return "Curse"
        if player.count_in_deck("Estate"):
            return "Estate"
        if player.count_in_deck("Copper"):
            return "Copper"
        return "Estate"
