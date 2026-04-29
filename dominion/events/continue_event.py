"""The Continue event from Plunder."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Continue(Event):
    """$8: gain a non-Victory non-Command card costing up to $4, then play it."""

    def __init__(self):
        super().__init__("Continue", CardCost(coins=8))

    def on_buy(self, game_state, player) -> None:
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_victory or card.is_command:
                continue
            if card.cost.potions > 0:
                continue
            if card.cost.coins > 4:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)

        if not candidates:
            return

        chosen = player.ai.choose_continue_target(game_state, player, candidates)
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return

        game_state.supply[chosen.name] -= 1
        game_state.log_callback(
            ("supply_change", chosen.name, -1, game_state.supply[chosen.name])
        )
        gained = game_state.gain_card(player, chosen)

        if not gained.is_action:
            return

        # Play the gained Action — pull it out of discard and resolve it.
        if gained in player.discard:
            player.discard.remove(gained)
        player.in_play.append(gained)
        # Continue grants a free play; we deliberately don't deduct an action.
        gained.on_play(game_state)
