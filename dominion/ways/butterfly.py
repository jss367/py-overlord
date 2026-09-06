from dominion.cards.base_card import Card
from .base_way import Way
from .horse import _resolve_pile_name


class WayOfTheButterfly(Way):
    """Return the played card to its pile to gain a card costing $1 more."""

    def __init__(self):
        super().__init__("Way of the Butterfly")

    def apply(self, game_state, card: Card) -> None:
        player = game_state.current_player

        # "You may return this to its pile. If you do, gain a card costing
        # exactly $1 more." A card that is not in play (Riverboat's set-aside
        # card, Captain's Supply proxy, a Throne Room replay after an earlier
        # Way moved it) cannot be returned, so nothing is gained either.
        if card not in player.in_play:
            return
        # Return the card to its OWNING pile, as Way of the Horse does. A
        # Knight or Ruins variant (Dame Anna, Ruined Library...) lives under
        # the shared "Knights"/"Ruins" key, not under ``card.name``; a card
        # with no resolvable pile cannot be returned, so it stays in play and
        # nothing is gained.
        pile_name = _resolve_pile_name(game_state, card)
        if pile_name is None:
            return
        player.in_play.remove(card)
        # Leaving play ends any Frog marker from an earlier play this turn.
        card._frog_topdeck = None
        game_state.supply[pile_name] = game_state.supply.get(pile_name, 0) + 1
        if pile_name in game_state.pile_order:
            game_state.pile_order[pile_name].append(card.name)

        target_cost = card.cost.coins + 1

        # Collect all gainable cards at the target cost
        candidates = []
        for _name, candidate, _count in game_state._iter_gainable_supply_cards():
            if (
                candidate.cost.coins == target_cost
                and candidate.cost.potions == card.cost.potions
            ):
                candidates.append(candidate)

        if not candidates:
            return

        # Let the AI choose which card to gain
        if len(candidates) == 1:
            chosen = candidates[0]
        else:
            chosen = player.ai.choose_buy(game_state, candidates + [None])

        if chosen is not None:
            game_state.supply[chosen.name] -= 1
            game_state.log_callback(
                ("supply_change", chosen.name, -1, game_state.supply[chosen.name])
            )
            game_state.log_callback(
                ("action", player.ai.name,
                 f"gains {chosen.name} via Way of the Butterfly (returned {card.name})",
                 {})
            )
            game_state.gain_card(player, chosen)
