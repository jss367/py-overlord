from .base_ally import Ally


class CoastalHaven(Ally):
    """At end of turn, you may spend 1 Favor per card to keep cards in
    hand for next turn.

    Simplified: keep up to (favors) Action / Treasure cards from hand
    by setting them aside in ``foresight_set_aside`` (re-used as a
    generic "keep across turns" zone). They re-enter hand at end of
    cleanup, mimicking the official effect.
    """

    def __init__(self):
        super().__init__("Coastal Haven")

    def on_turn_end(self, game_state, player) -> None:
        if player.favors <= 0 or not player.hand:
            return
        # Decide how many to keep: Action cards first, then Treasures > 1$.
        kept: list = []
        capacity = player.favors
        # Sort hand by usefulness (Actions first, then expensive treasures).
        priority = sorted(
            player.hand,
            key=lambda c: (
                -1 * c.is_action,
                -1 * (c.is_treasure and c.cost.coins >= 3),
                -c.cost.coins,
            ),
        )
        for card in priority:
            if capacity <= 0:
                break
            if not (card.is_action or (card.is_treasure and card.cost.coins >= 3)):
                continue
            kept.append(card)
            capacity -= 1
        if not kept:
            return
        spent = len(kept)
        player.favors -= spent
        for card in kept:
            if card in player.hand:
                player.hand.remove(card)
        player.foresight_set_aside.extend(kept)
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends {spent} Favors on Coastal Haven to keep {len(kept)} cards",
                {"favors_remaining": player.favors},
            )
        )
