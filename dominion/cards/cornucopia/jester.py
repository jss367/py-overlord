from ..base_card import Card, CardCost, CardStats, CardType


class Jester(Card):
    """Provides coins and hands out cards or curses."""

    def __init__(self):
        super().__init__(
            name="Jester",
            cost=CardCost(coins=5),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if not target.deck and target.discard:
                target.shuffle_discard_into_deck()
            if not target.deck:
                return

            revealed = target.deck.pop()
            game_state.discard_card(target, revealed)

            if revealed.is_victory:
                game_state.give_curse_to_player(target)
                return

            if game_state.supply.get(revealed.name, 0) <= 0:
                return

            from ..registry import get_card

            gained = get_card(revealed.name)
            game_state.supply[revealed.name] -= 1
            game_state.gain_card(target, gained)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
