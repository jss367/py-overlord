"""Renaissance Artifacts: persistent tokens that pass between players.

Artifacts are not cards. Each Artifact has at most one holder at a time.
When the triggering Kingdom card (Flag Bearer / Border Guard /
Treasurer / Swashbuckler) is played, the player playing it takes the
relevant Artifact from whoever held it (or from no one if it was
unheld). Artifact effects fire only for the current holder and are
implemented as hook methods invoked by ``GameState`` and the cards.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState


class Artifact:
    """Base Artifact class.

    Subclasses override the relevant hook(s) to apply their effect for
    the current holder. ``on_take`` and ``on_lose`` are called when
    ownership changes; the default implementations are no-ops.
    """

    name: str = ""

    def __init__(self) -> None:
        self.holder: Optional["PlayerState"] = None

    # ------------------------------------------------------------------
    # Ownership lifecycle
    # ------------------------------------------------------------------
    def on_take(self, state: "GameState", player: "PlayerState") -> None:
        """Called when ``player`` takes this Artifact."""

    def on_lose(self, state: "GameState", player: "PlayerState") -> None:
        """Called when ``player`` loses this Artifact (someone else took it)."""

    # ------------------------------------------------------------------
    # Effect hooks – overridden by individual artifacts
    # ------------------------------------------------------------------
    def on_holder_turn_start(self, state: "GameState", player: "PlayerState") -> None:
        """Fire at the start of the holder's turn (Flag, Key)."""

    def on_holder_buy_phase_start(
        self, state: "GameState", player: "PlayerState"
    ) -> None:
        """Fire at the start of the holder's Buy phase (Treasure Chest)."""

    def on_holder_play_border_guard(
        self, state: "GameState", player: "PlayerState", border_guard
    ) -> None:
        """Fire when the holder plays a Border Guard (Horn, Lantern)."""

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"Artifact({self.name})"
