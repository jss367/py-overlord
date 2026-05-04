"""Sinister Plot: at the start of your turn, add a token to this, or remove
all tokens for +X Cards (X = tokens removed)."""

from dominion.cards.base_card import CardCost

from .base_project import Project


class SinisterPlot(Project):
    def __init__(self) -> None:
        super().__init__("Sinister Plot", CardCost(coins=4))
        # Tokens are tracked per (project, player). Since each player buys
        # their own copy of the project (added to player.projects), the
        # instance state is per-player.
        self.tokens = 0

    def on_turn_start(self, game_state, player) -> None:
        # Heuristic: cash in when we have 3+ tokens; otherwise stockpile.
        # The AI may override later; default keeps us building cards for
        # explosive draws.
        if self.tokens >= 3:
            # Remove a token, then +X Cards where X = remaining tokens.
            self.tokens -= 1
            if self.tokens > 0:
                game_state.draw_cards(player, self.tokens)
        else:
            self.tokens += 1
