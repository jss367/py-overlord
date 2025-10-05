from ..base_card import Card, CardCost, CardStats, CardType


class Legionary(Card):
    def __init__(self):
        super().__init__(
            name="Legionary",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        has_gold = any(card.name == "Gold" for card in player.hand)
        if not has_gold:
            return

        if not player.ai.should_reveal_gold_for_legionary(game_state, player):
            return

        def attack(target):
            if len(target.hand) <= 2:
                return

            discard_needed = len(target.hand) - 2
            selected = target.ai.choose_cards_to_discard(
                game_state,
                target,
                list(target.hand),
                discard_needed,
                reason="legionary",
            )

            discarded = []

            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)
                    discarded.append(card)

            while len(target.hand) > 2:
                card = min(target.hand, key=self._discard_priority)
                target.hand.remove(card)
                game_state.discard_card(target, card)
                discarded.append(card)

            if discarded:
                game_state.draw_cards(target, 1)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
