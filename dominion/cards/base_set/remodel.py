"""Implementation of the Remodel trasher."""

from ..base_card import Card, CardCost, CardStats, CardType


class Remodel(Card):
    def __init__(self):
        super().__init__(
            name="Remodel",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from dominion.ai import tactical_defaults
        from ..gain_decisions import (
            choose_free_gain, gain_menu, gain_selected, resolve_gain,
        )

        player = game_state.current_player
        if not player.hand:
            return
        options = [
            (card, gain_menu(game_state, player, self._limit(game_state, player, card)))
            for card in player.hand
        ]
        hook = getattr(player.ai, "choose_remodel_option", None)
        pair = hook(game_state, player, options) if hook else None
        if not isinstance(pair, tuple) or len(pair) != 2 or pair[0] not in player.hand:
            pair = tactical_defaults.choose_remodel_option(
                game_state, player, options,
                lambda state, owner, choices, context: choose_free_gain(
                    state, owner, choices, "Remodel", context.sacrificed
                ),
            )
        trashed, target = pair
        if trashed is None:
            return
        prepare = getattr(player.ai, "prepare_remodel_trash_record", None)
        commit_trash = prepare(game_state, player, list(player.hand), trashed) if prepare else None
        player.hand.remove(trashed)
        game_state.trash_card(player, trashed)
        if commit_trash is not None:
            commit_trash(trashed)
        # Follow instructions in order: trash/reactions, then check the
        # trashed card's current cost and the available replacement gains.
        limit = self._limit(game_state, player, trashed)
        choices = gain_menu(game_state, player, limit)
        target = resolve_gain(target, choices) or choose_free_gain(
            game_state, player, choices, "Remodel", trashed
        )
        gain_selected(game_state, player, target, choices=choices, source="Remodel", sacrificed=trashed)

    @staticmethod
    def _limit(state, player, card):
        return CardCost(state.get_card_cost(player, card) + 2,
                        card.cost.potions, card.cost.debt)
