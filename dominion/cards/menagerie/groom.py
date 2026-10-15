"""Groom - Action from Menagerie."""

from ..base_card import Card, CardCost, CardStats, CardType


class Groom(Card):
    """Gain a card costing up to $4. If it's an Action, gain a Horse; if a
    Treasure, gain a Silver; if a Victory, +1 Card and +1 Action.
    """

    def __init__(self):
        super().__init__(
            name="Groom",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def get_additional_non_supply_piles(self) -> dict[str, int]:
        from .supplies import HORSE_PILE_COUNT

        return {"Horse": HORSE_PILE_COUNT}

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name in game_state.non_supply_pile_names:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if (
                card.may_be_gained(game_state)
                and card.cost.coins <= 4
                and card.cost.potions == 0
            ):
                candidates.append(card)
        if not candidates:
            return

        choice = player.ai.choose_buy(game_state, candidates + [None])
        if choice is None:
            choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        from ..gain_decisions import gained_card_types

        types_at_gain = []
        game_state.gain_card(player, choice, gain_observer=lambda c: types_at_gain.append(
            gained_card_types(game_state, player, c)
        ))
        if not types_at_gain:
            return
        action, treasure, victory = types_at_gain[0]

        if action:
            if game_state.supply.get("Horse", 0) > 0:
                game_state.supply["Horse"] -= 1
                game_state.gain_card(player, get_card("Horse"))
        if treasure:
            if game_state.supply.get("Silver", 0) > 0:
                game_state.supply["Silver"] -= 1
                game_state.gain_card(player, get_card("Silver"))
        if victory:
            game_state.draw_cards(player, 1)
            if not player.ignore_action_bonuses:
                player.actions += 1
