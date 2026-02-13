from dominion.cards.registry import get_card
from dominion.cards.base_card import Card
from .base_way import Way


class WayOfTheButterfly(Way):
    """Return the played card to its pile to gain a card costing $1 more."""

    def __init__(self):
        super().__init__("Way of the Butterfly")

    def apply(self, game_state, card: Card) -> None:
        player = game_state.current_player

        # Return the card to its supply pile
        if card in player.in_play:
            player.in_play.remove(card)
        game_state.supply[card.name] = game_state.supply.get(card.name, 0) + 1

        target_cost = card.cost.coins + 1

        # Collect all gainable cards at the target cost
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
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
            game_state.gain_card(player, chosen)
