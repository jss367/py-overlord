"""Horn artifact: when its holder discards a Border Guard from play, they
may put it onto their deck instead."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_artifact import Artifact

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState


class Horn(Artifact):
    name = "Horn"

    def on_holder_play_border_guard(
        self, state: "GameState", player: "PlayerState", border_guard
    ) -> None:
        # Per Renaissance rules, the Horn lets the holder topdeck the
        # Border Guard once it would be discarded (i.e. at end of play
        # or cleanup). We model this by setting a flag on the card so
        # cleanup picks it up; Border Guard checks for an active Horn
        # holder when discarding from play and topdecks itself.
        border_guard.horn_topdeck_pending = True
