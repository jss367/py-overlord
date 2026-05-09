from ..base_card import Card, CardCost, CardStats, CardType


class Charlatan(Card):
    """Action-Attack ($5): +$3. Each other player gains a Curse.

    In any kingdom that includes Charlatan, Curses are Treasures (in
    addition to their other types) and produce $1 when played — for the
    entire game and in all situations. The Curse-as-Treasure effect is
    wired in :meth:`GameState.handle_treasure_phase` and keyed off
    Charlatan's presence in the Supply.
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
