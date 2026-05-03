"""Base class for Rising Sun Prophecies.

A Prophecy is a global rule change that activates once all Sun tokens are
removed from it. Until then it sits on the table and doesn't do anything.
Omens are how Sun tokens get removed (each Omen produces +1 Sun token,
which removes one from the active Prophecy).
"""

from dataclasses import dataclass


@dataclass
class Prophecy:
    name: str = "Prophecy"
    description: str = ""

    def __post_init__(self):
        self.is_active = False

    def setup(self, game_state) -> None:
        """Called once at game start. Override for prophecies that change
        the supply or game setup (e.g. Approaching Army adds an Attack pile).
        """
        pass

    def activate(self, game_state) -> None:
        """Called when the last Sun token is removed."""
        self.is_active = True
        game_state.log_callback(("action", "Prophecy", f"{self.name} activates", {}))
        self.on_activate(game_state)

    def on_activate(self, game_state) -> None:
        """Override for prophecies whose effect fires once on activation
        (e.g. Divine Wind, Kind Emperor's first trigger).
        """
        pass

    # ------------------------------------------------------------------
    # Hooks called from game_state. Default no-ops; override as needed.
    # ------------------------------------------------------------------

    def on_play_action(self, game_state, player, card) -> None:
        """Fired after each Action card finishes resolving while active."""
        pass

    def on_play_treasure(self, game_state, player, card) -> None:
        """Fired after each Treasure card resolves while active."""
        pass

    def on_play_attack(self, game_state, player, card) -> None:
        """Fired after each Attack card finishes resolving while active.

        Used by Approaching Army (+$1 from each Attack played).
        """
        pass

    def on_gain(self, game_state, player, card) -> None:
        """Fired after a card is gained while active."""
        pass

    def on_turn_start(self, game_state, player) -> None:
        """Fired at the start of each player's turn while active."""
        pass

    def on_cleanup_start(self, game_state, player) -> None:
        """Fired at the start of cleanup, before discarding hand."""
        pass

    def cost_modifier(self, game_state, player, card) -> int:
        """Return a modifier applied to the card's coin cost. Negative reduces."""
        return 0
