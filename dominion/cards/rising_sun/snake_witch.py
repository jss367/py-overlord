from ..base_card import Card, CardCost, CardStats, CardType


class SnakeWitch(Card):
    """Action-Attack ($2): +1 Card, +1 Action.
    You may reveal your hand. If all cards in it have different names, return
    Snake Witch to its pile, and if you did, each other player gains a Curse.
    """

    def __init__(self):
        super().__init__(
            name="Snake Witch",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        # Reveal hand: optional. Skip if hand has duplicates or AI declines.
        names = [c.name for c in player.hand]
        all_different = len(set(names)) == len(names)
        if not all_different:
            return
        if not player.ai.should_reveal_snake_witch(game_state, player):
            return

        # Return Snake Witch from in_play to its pile, then curse opponents.
        if self in player.in_play:
            player.in_play.remove(self)
            game_state.supply["Snake Witch"] = game_state.supply.get("Snake Witch", 0) + 1
        else:
            return

        from ..registry import get_card

        for other in game_state.players:
            if other is player:
                continue

            def attack_target(target):
                if game_state.supply.get("Curse", 0) <= 0:
                    return
                game_state.supply["Curse"] -= 1
                game_state.gain_card(target, get_card("Curse"))

            game_state.attack_player(other, attack_target)
