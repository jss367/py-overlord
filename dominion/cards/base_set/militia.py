"""Implementation of the Militia attack."""

from ..base_card import Card, CardCost, CardStats, CardType


class Militia(Card):
    def __init__(self):
        super().__init__(
            name="Militia",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) <= 3:
                return

            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="militia"
            )

            discarded: list = []
            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
                    discarded.append(card)

            while len(target.hand) > 3:
                card = min(target.hand, key=self._discard_priority)
                target.hand.remove(card)
                game_state.discard_card(target, card)
                discarded.append(card)

            if discarded:
                context = {
                    "discarded_cards": [c.name for c in discarded],
                    "remaining_hand": [c.name for c in target.hand],
                }
                game_state.log_callback(
                    ("action", target.ai.name, "discards to 3 cards due to Militia", context)
                )

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
