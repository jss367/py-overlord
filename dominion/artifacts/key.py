"""Key artifact: holder gets +$1 at the start of their turn."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_artifact import Artifact

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState


class Key(Artifact):
    name = "Key"

    def on_holder_turn_start(self, state: "GameState", player: "PlayerState") -> None:
        player.coins += 1
