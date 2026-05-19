from .base_ally import Ally


class CoastalHaven(Ally):
    """At end of turn, you may spend 1 Favor per card to keep cards in
    hand for next turn.

    Cards are set aside in ``foresight_set_aside`` and re-enter hand at end
    of cleanup, after the next hand is drawn.
    """

    def __init__(self):
        super().__init__("Coastal Haven")

    def on_turn_end(self, game_state, player) -> None:
        if player.favors <= 0 or not player.hand:
            return
        choices = list(player.hand)
        selected = player.ai.choose_cards_for_coastal_haven(
            game_state, player, choices, player.favors
        )
        kept: list = []
        seen: set[int] = set()
        for card in selected:
            if len(kept) >= player.favors:
                break
            if card not in player.hand or id(card) in seen:
                continue
            kept.append(card)
            seen.add(id(card))
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
