from .base_ally import Ally


class FamilyOfInventors(Ally):
    """At end of turn, spend 1 Favor to put a -$1 cost token on a Supply
    pile.

    Implementation: stash the discount on ``GameState.family_inventors``
    map (pile_name -> total tokens). The discount is applied via
    ``cost_modifier`` injected on each card lookup.

    Since we don't have a global cost modifier hook here, we apply the
    discount through ``GameState.get_card_cost``: the loop checks the
    map and reduces cost accordingly.
    """

    def __init__(self):
        super().__init__("Family of Inventors")

    def on_turn_end(self, game_state, player) -> None:
        if player.favors <= 0:
            return
        # Pick a useful pile that the player wants to buy soon.
        # Prefer expensive Action cards in the supply.
        from dominion.cards.registry import get_card

        target_name: str | None = None
        target_score = -1
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            if name in {"Curse", "Copper", "Silver", "Gold", "Platinum",
                        "Estate", "Duchy", "Province", "Colony"}:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not (card.is_action or card.is_treasure):
                continue
            score = card.cost.coins
            if score > target_score:
                target_score = score
                target_name = name
        if target_name is None:
            return
        player.favors -= 1
        if not hasattr(game_state, "family_inventor_tokens"):
            game_state.family_inventor_tokens = {}
        game_state.family_inventor_tokens[target_name] = (
            game_state.family_inventor_tokens.get(target_name, 0) + 1
        )
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends a Favor on Family of Inventors (-$1 on {target_name})",
                {"favors_remaining": player.favors},
            )
        )
