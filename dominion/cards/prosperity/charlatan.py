from ..base_card import Card, CardCost, CardStats, CardType


class Charlatan(Card):
    """Action-Attack ($5): +$3. Each other player gains a Curse.

    On the printed card Charlatan also makes Curse cards in the supply
    "count as Curse-typed Treasures" for cost purposes; this implementation
    treats Charlatan as a stronger Witch-style attack with +$3.
    """

    def __init__(self):
        super().__init__(
            name="Charlatan",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        current_player = game_state.current_player

        def curse_target(target):
            if game_state.supply.get("Curse", 0) > 0:
                game_state.give_curse_to_player(target)

        for player in game_state.players:
            if player is current_player:
                continue
            game_state.attack_player(player, curse_target)
