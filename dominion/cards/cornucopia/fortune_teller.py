from ..base_card import Card, CardCost, CardStats, CardType


class FortuneTeller(Card):
    """Provides +2 coins and attacks opponents by scrying their decks."""

    def __init__(self):
        super().__init__(
            name="Fortune Teller",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            revealed: list = []
            while True:
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break

                card = target.deck.pop()
                if card.is_victory or card.name == "Curse":
                    target.deck.append(card)
                    break

                revealed.append(card)

            if revealed:
                game_state.discard_cards(target, revealed)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
