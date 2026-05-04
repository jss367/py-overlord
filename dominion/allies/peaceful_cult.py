from .base_ally import Ally


class PeacefulCult(Ally):
    """At start of Buy phase, may spend any number of Favors to trash
    that many cards from hand.
    """

    def __init__(self):
        super().__init__("Peaceful Cult")

    def on_buy_phase_start(self, game_state, player) -> None:
        # Spend per junk card; cap by available Favors.
        if player.favors <= 0 or not player.hand:
            return
        # Identify trash-worthy cards.
        worthy = [
            c for c in player.hand
            if c.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}
            or (c.is_victory and not c.is_action and c.cost.coins <= 2)
        ]
        if not worthy:
            return
        spend = min(player.favors, len(worthy))
        # Trash from worst to best.
        worthy_sorted = sorted(
            worthy,
            key=lambda c: (c.name == "Curse", c.name == "Copper", c.cost.coins),
            reverse=True,
        )
        trashed = 0
        for card in worthy_sorted[:spend]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
                trashed += 1
        if trashed <= 0:
            return
        player.favors -= trashed
        game_state.log_callback(
            (
                "action",
                player.ai.name,
                f"spends {trashed} Favors on Peaceful Cult (trash {trashed} cards)",
                {"favors_remaining": player.favors},
            )
        )
