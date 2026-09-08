from .base_ally import Ally
from ..cards.allies._rules import decide


class OrderOfMasons(Ally):
    def __init__(self):
        super().__init__("Order of Masons")

    def on_shuffle(self, game_state, player, cards):
        if player.favors < 1:
            return [], []
        junk = [
            c
            for c in cards
            if c.name in {"Curse", "Estate", "Copper", "Hovel", "Overgrown Estate"}
        ]
        default = min(player.favors, (len(junk) + 1) // 2)
        spend = decide(
            game_state, player, "masons_favors", list(range(player.favors + 1)), default
        )
        if not spend:
            return [], []
        player.favors -= spend
        remaining = list(cards)
        omitted = []
        for _ in range(min(2 * spend, len(cards))):
            default = next((c for c in junk if c in remaining), None)
            chosen = decide(
                game_state, player, "masons_discard", [None] + remaining, default
            )
            if chosen is None:
                break
            remaining.remove(chosen)
            omitted.append(chosen)
        return [], omitted
