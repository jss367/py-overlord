from ..base_card import Card, CardCost, CardStats, CardType


class Loan(Card):
    def __init__(self):
        super().__init__(
            name="Loan",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        revealed = []
        revealed_treasure = None
        while player.deck or player.discard:
            if not player.deck:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            card = player.deck.pop()
            if card.is_treasure:
                revealed_treasure = card
                break
            revealed.append(card)

        if revealed:
            player.discard.extend(revealed)

        if revealed_treasure is None:
            return

        choice = player.ai.choose_card_to_trash(
            game_state, [revealed_treasure, None]
        )
        if choice is revealed_treasure:
            game_state.trash_card(player, revealed_treasure)
        else:
            game_state.discard_card(player, revealed_treasure)
