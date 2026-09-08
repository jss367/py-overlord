from .base_ally import Ally
from ..cards.allies._rules import decide


class OrderOfAstrologers(Ally):
    def __init__(self):
        super().__init__("Order of Astrologers")

    def on_shuffle(self, game_state, player, cards):
        if player.favors < 1:
            return [], []
        default = min(player.favors, len(cards))
        spend = decide(
            game_state,
            player,
            "astrologers_favors",
            list(range(player.favors + 1)),
            default,
        )
        if not spend:
            return [], []
        player.favors -= spend
        remaining = list(cards)
        top = []
        for _ in range(min(spend, len(remaining))):
            default = max(
                remaining, key=lambda c: (c.is_action, c.is_treasure, c.cost.coins)
            )
            chosen = decide(
                game_state, player, "astrologers_topdeck", remaining, default
            )
            remaining.remove(chosen)
            top.append(chosen)
        return top, []
