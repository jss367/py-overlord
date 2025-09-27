from ..base_card import Card, CardCost, CardStats, CardType


class Giant(Card):
    """Implements the Journey token flipping attack."""

    def __init__(self):
        super().__init__(
            name="Giant",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.journey_token_face_up = not player.journey_token_face_up

        if not player.journey_token_face_up:
            player.coins += 1
            return

        player.coins += 5

        def attack_target(target):
            if not target.deck and target.discard:
                target.shuffle_discard_into_deck()
            if not target.deck:
                game_state.give_curse_to_player(target)
                return

            revealed = target.deck.pop()
            cost = revealed.cost.coins
            if 3 <= cost <= 6:
                game_state.trash_card(target, revealed)
            else:
                target.discard.append(revealed)
                game_state.give_curse_to_player(target)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
