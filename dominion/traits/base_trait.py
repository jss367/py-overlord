"""Base class for Plunder Traits."""

from dataclasses import dataclass


@dataclass
class Trait:
    """A Trait attaches a persistent rules-modifier to one Kingdom pile.

    Subclasses (or instances built via the registry) implement :meth:`apply`
    to register state on the ``GameState`` so the rest of the engine can
    consult it during the relevant hook (gain / play / discard / shuffle / ...).
    """

    name: str

    def apply(self, game_state, target_pile_name: str) -> None:  # pragma: no cover
        """Attach this trait to the named supply pile in ``game_state``."""
        raise NotImplementedError
