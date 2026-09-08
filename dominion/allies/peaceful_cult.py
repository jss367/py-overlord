from .base_ally import Ally
from ..cards.allies._rules import decide


class PeacefulCult(Ally):
    def __init__(self):
        super().__init__("Peaceful Cult")

    def on_buy_phase_start(self, game_state, player):
        junk = [
            c
            for c in player.hand
            if c.name in {"Curse", "Estate", "Copper", "Hovel", "Overgrown Estate"}
        ]
        count = decide(
            game_state,
            player,
            "peaceful_cult_favors",
            list(range(player.favors + 1)),
            min(player.favors, len(junk)),
        )
        if not count:
            return
        player.favors -= count
        remaining = list(player.hand)
        selected = []
        for _ in range(min(count, len(remaining))):
            default = next((c for c in junk if c in remaining), remaining[0])
            chosen = decide(
                game_state, player, "peaceful_cult_trash", remaining, default
            )
            remaining.remove(chosen)
            selected.append(chosen)
        for card in selected:
            player.hand.remove(card)
        game_state.trash_cards_together(player, selected)
