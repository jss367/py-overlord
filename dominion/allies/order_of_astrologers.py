from .base_ally import Ally


class OrderOfAstrologers(Ally):
    """When you shuffle, may put 1 card per Favor on top.

    Implementation: at start of turn, if Favors > 0 and the next draw
    will trigger a shuffle (deck is empty or smaller than 5), pull up
    to ``favors`` good cards from the discard onto the deck — this
    approximates the official "rearrange the shuffle" effect.
    """

    def __init__(self):
        super().__init__("Order of Astrologers")

    def on_turn_start(self, game_state, player) -> None:
        if player.favors <= 0:
            return
        # Only fire when a shuffle is imminent (draw will need it).
        if len(player.deck) >= 5:
            return
        if not player.discard:
            return
        # Pick the best cards from the discard and topdeck them.
        spend = min(player.favors, len(player.discard), 5)
        if spend <= 0:
            return
        # Score: prefer Actions, then expensive Treasures.
        candidates = sorted(
            player.discard,
            key=lambda c: (
                c.is_action,
                c.is_treasure and c.cost.coins >= 3,
                c.cost.coins,
                c.name,
            ),
            reverse=True,
        )
        moved = []
        for card in candidates[:spend]:
            if card in player.discard:
                player.discard.remove(card)
                player.deck.append(card)
                moved.append(card)
        spent = len(moved)
        if spent <= 0:
            return
        player.favors -= spent
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends {spent} Favors on Order of Astrologers (topdeck {spent} cards)",
                {"favors_remaining": player.favors},
            )
        )
