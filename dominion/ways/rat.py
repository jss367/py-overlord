"""Way of the Rat — Discard a Treasure. Gain an Action card costing up to $5."""

from .base_way import Way


class WayOfTheRat(Way):
    def __init__(self):
        super().__init__("Way of the Rat")

    def apply(self, game_state, card) -> None:
        from dominion.cards.registry import get_card

        player = game_state.current_player
        treasures = [c for c in player.hand if c.is_treasure]
        if not treasures:
            return

        # Pick cheapest treasure to discard
        choice = min(treasures, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(choice)
        game_state.discard_card(player, choice)

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                cand = get_card(name)
            except ValueError:
                continue
            if cand.is_action and cand.cost.coins <= 5 and cand.cost.potions == 0:
                candidates.append(cand)
        if not candidates:
            return
        gain_choice = player.ai.choose_buy(game_state, candidates + [None])
        if gain_choice is None:
            gain_choice = max(candidates, key=lambda c: (c.cost.coins, c.name))
        if game_state.supply.get(gain_choice.name, 0) <= 0:
            return
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, gain_choice)
