from ..base_card import Card, CardCost, CardStats, CardType


class Clerk(Card):
    """Action-Attack-Reaction ($4): +$2. Each other player with 5 or more
    cards in hand puts one of them onto their deck. At the start of your
    turn, you may play this from your hand.
    """

    def __init__(self):
        super().__init__(
            name="Clerk",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.REACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        def attack_target(target):
            if len(target.hand) < 5:
                return
            choice = target.ai.choose_card_to_topdeck_for_clerk(
                game_state, target, list(target.hand)
            )
            if choice is None or choice not in target.hand:
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
