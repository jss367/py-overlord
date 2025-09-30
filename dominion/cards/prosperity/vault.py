from ..base_card import Card, CardCost, CardStats, CardType


class Vault(Card):
    def __init__(self):
        super().__init__(
            name="Vault",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        if player.hand:
            choices = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), len(player.hand), reason="vault"
            )
            discarded: list = []
            for card in choices:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
                    discarded.append(card)
            player.coins += len(discarded)

        for other in game_state.players:
            if other is player or len(other.hand) < 2:
                continue

            if not other.ai.should_discard_for_vault(game_state, other):
                continue

            selected = other.ai.choose_cards_to_discard(
                game_state, other, list(other.hand), 2, reason="vault"
            )
            if len(selected) < 2:
                continue

            discarded: list = []
            for card in selected[:2]:
                if card in other.hand:
                    other.hand.remove(card)
                    game_state.discard_card(other, card)
                    discarded.append(card)

            if len(discarded) == 2:
                game_state.draw_cards(other, 1)
