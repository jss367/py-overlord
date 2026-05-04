"""Old Witch: Action-Attack ($5). +3 Cards.

Each other player gains a Curse and may trash a Curse from their hand.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class OldWitch(Card):
    def __init__(self) -> None:
        super().__init__(
            name="Old Witch",
            cost=CardCost(coins=5),
            stats=CardStats(cards=3),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        attacker = game_state.current_player

        def attack(target):
            if game_state.supply.get("Curse", 0) > 0:
                game_state.give_curse_to_player(target)

            curse_in_hand = next(
                (c for c in target.hand if c.name == "Curse"), None
            )
            if curse_in_hand is not None:
                target.hand.remove(curse_in_hand)
                game_state.trash_card(target, curse_in_hand)

        for player in game_state.players:
            if player is attacker:
                continue
            game_state.attack_player(player, attack, attacker=attacker, attack_card=self)
