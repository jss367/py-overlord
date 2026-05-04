"""Treasure Chest artifact: holder gains a Gold at the start of Buy phase."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base_artifact import Artifact

if TYPE_CHECKING:  # pragma: no cover - typing only
    from dominion.game.game_state import GameState
    from dominion.game.player_state import PlayerState


class TreasureChest(Artifact):
    name = "Treasure Chest"

    def on_holder_buy_phase_start(
        self, state: "GameState", player: "PlayerState"
    ) -> None:
        if state.supply.get("Gold", 0) <= 0:
            return
        from dominion.cards.registry import get_card

        state.supply["Gold"] -= 1
        state.gain_card(player, get_card("Gold"))
