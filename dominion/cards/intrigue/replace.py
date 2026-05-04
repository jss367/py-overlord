"""Implementation of Replace."""

from ..base_card import Card, CardCost, CardStats, CardType


class Replace(Card):
    """Trash a card from your hand. Gain a card costing up to $2 more.
    If it's an Action or Treasure, put it onto your deck; if it's a
    Victory card, each other player gains a Curse."""

    def __init__(self):
        super().__init__(
            name="Replace",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        chosen = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if chosen is None or chosen not in player.hand:
            return

        trash_cost = chosen.cost.coins
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        max_cost = trash_cost + 2
        target = player.ai.choose_card_to_gain_for_replace(
            game_state, player, max_cost
        )
        if target is None or game_state.supply.get(target.name, 0) <= 0:
            return

        game_state.supply[target.name] -= 1
        game_state.log_callback(
            ("supply_change", target.name, -1, game_state.supply[target.name])
        )

        is_action_or_treasure = target.is_action or target.is_treasure
        gained = game_state.gain_card(
            player, target, to_deck=is_action_or_treasure
        )

        if gained.is_victory:
            # Each other player gains a Curse. Replace is an Attack.
            def curse_target(other):
                game_state.give_curse_to_player(other)

            for other in game_state.players:
                if other is player:
                    continue
                game_state.attack_player(other, curse_target)
