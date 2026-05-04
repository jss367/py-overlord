"""Implementation of Upgrade."""

from ..base_card import Card, CardCost, CardStats, CardType


class Upgrade(Card):
    """+1 Card +1 Action. Trash a card from your hand. Gain a card costing
    exactly $1 more."""

    def __init__(self):
        super().__init__(
            name="Upgrade",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        chosen = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if chosen is None or chosen not in player.hand:
            return

        trash_cost = chosen.cost.coins
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        target = player.ai.choose_card_to_gain_for_upgrade(
            game_state, player, trash_cost + 1
        )
        if target is None or game_state.supply.get(target.name, 0) <= 0:
            return

        game_state.supply[target.name] -= 1
        game_state.log_callback(
            ("supply_change", target.name, -1, game_state.supply[target.name])
        )
        game_state.gain_card(player, target)
