from ..base_card import Card, CardCost, CardStats, CardType


class GhostShip(Card):
    """Action-Attack ($5): +2 Cards. Each other player with 4 or more cards in hand
    puts cards from their hand onto their deck (in any order) until they have 3
    cards in hand.
    """

    def __init__(self):
        super().__init__(
            name="Ghost Ship",
            cost=CardCost(coins=5),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) < 4:
                return

            to_topdeck = len(target.hand) - 3

            for _ in range(to_topdeck):
                choice = target.ai.choose_card_to_topdeck_from_hand(
                    game_state, target, list(target.hand), reason="ghost_ship"
                )
                if choice is None or choice not in target.hand:
                    # Fallback: put a low-value card on top
                    choice = min(
                        target.hand,
                        key=lambda c: (c.is_action, c.is_treasure, c.cost.coins, c.name),
                    )
                target.hand.remove(choice)
                target.deck.append(choice)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target)
