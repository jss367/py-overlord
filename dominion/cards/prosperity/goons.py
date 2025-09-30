from ..base_card import Card, CardCost, CardStats, CardType


class Goons(Card):
    def __init__(self):
        super().__init__(
            name="Goons",
            cost=CardCost(coins=6),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        player.goons_played += 1

        def attack_target(target):
            if len(target.hand) <= 3:
                return

            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), discard_needed, reason="goons"
            )

            discarded: list = []
            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
                    discarded.append(card)

            # Fallback in case the AI declined to discard enough cards
            def discard_priority(card):
                if card.name == "Curse":
                    return (0, card.name)
                if card.is_victory and not card.is_action:
                    return (1, card.cost.coins, card.name)
                if card.name == "Copper":
                    return (2, card.name)
                return (3, card.cost.coins, card.name)

            while len(target.hand) > 3:
                card = min(target.hand, key=discard_priority)
                target.hand.remove(card)
                game_state.discard_card(target, card)
                discarded.append(card)

            if discarded:
                context = {
                    "discarded_cards": [c.name for c in discarded],
                    "remaining_hand": [c.name for c in target.hand],
                }
                game_state.log_callback(
                    ("action", target.ai.name, "discards to 3 cards due to Goons", context)
                )

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
