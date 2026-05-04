from .base_ally import Ally


class TrappersLodge(Ally):
    """When you gain a card, may spend 1 Favor to topdeck it."""

    def __init__(self):
        super().__init__("Trappers' Lodge")

    def on_owner_gain(self, game_state, player, gained_card) -> None:
        if player.favors <= 0:
            return
        # Heuristic: topdeck Action / Treasure cards costing $3+.
        if gained_card.is_victory and not gained_card.is_action:
            return
        if gained_card.cost.coins < 3:
            return
        # Move the gained card from discard to top of deck if present.
        moved = False
        if gained_card in player.discard:
            player.discard.remove(gained_card)
            player.deck.append(gained_card)
            moved = True
        elif gained_card in player.deck and gained_card != (
            player.deck[-1] if player.deck else None
        ):
            player.deck.remove(gained_card)
            player.deck.append(gained_card)
            moved = True
        if not moved:
            return
        player.favors -= 1
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends a Favor on Trappers' Lodge to topdeck {gained_card}",
                {"favors_remaining": player.favors},
            )
        )
