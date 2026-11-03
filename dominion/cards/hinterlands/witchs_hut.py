from ..base_card import Card, CardCost, CardStats, CardType


class WitchsHut(Card):
    def __init__(self):
        super().__init__(
            name="Witch's Hut",
            cost=CardCost(coins=5),
            stats=CardStats(cards=4),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        from ._discard import discard_from_hand

        discards = discard_from_hand(game_state, player, 2, "witchs_hut")
        actions_discarded = len(discards) == 2 and all(game_state.is_action(card) for card in discards)

        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                if actions_discarded:
                    game_state.give_curse_to_player(target)

            # Guard Dog can react to the Attack even when no Curse is given.
            game_state.attack_player(other, attack)
