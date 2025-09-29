from ..base_card import CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard


class Catapult(TopSplitPileCard):
    """Simplified Catapult that trashes a card for coins and attacks opponents."""

    partner_card_name = "Rocks"

    def __init__(self):
        super().__init__(
            name="Catapult",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if to_trash is None:
            # Default to trashing lowest-cost card to keep the effect flowing
            to_trash = min(player.hand, key=lambda c: c.cost.coins)
        if to_trash in player.hand:
            player.hand.remove(to_trash)
            game_state.trash_card(player, to_trash)
            player.coins += min(2, to_trash.cost.coins)

        def attack(target):
            while len(target.hand) > 3:
                target.discard.append(target.hand.pop())

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack)
