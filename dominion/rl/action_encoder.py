"""Encodes actions (card choices) to/from integer indices."""

from typing import Optional
import numpy as np
from dominion.cards.base_card import Card
from dominion.cards.registry import get_card


BASE_CARDS = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"]


class ActionEncoder:
    """Maps between card choices and action indices.

    Action space is:
    - Index 0 to N-1: One index per card type (base + kingdom)
    - Index N: Pass/None action
    """

    def __init__(self, kingdom_cards: list[str]):
        """Initialize encoder with kingdom card names."""
        self.kingdom_cards = list(kingdom_cards)
        self.all_cards = BASE_CARDS + self.kingdom_cards
        self.card_to_idx = {name: i for i, name in enumerate(self.all_cards)}
        self._pass_index = len(self.all_cards)
        self._action_size = len(self.all_cards) + 1

    @property
    def action_size(self) -> int:
        """Total number of possible actions."""
        return self._action_size

    @property
    def pass_action_index(self) -> int:
        """Index of the pass/None action."""
        return self._pass_index

    def card_to_action(self, card: Optional[Card]) -> int:
        """Convert a card (or None) to an action index."""
        if card is None:
            return self._pass_index
        return self.card_to_idx[card.name]

    def action_to_card(self, action: int) -> Optional[Card]:
        """Convert an action index to a card (or None)."""
        if action == self._pass_index:
            return None
        card_name = self.all_cards[action]
        return get_card(card_name)

    def get_action_mask(self, choices: list[Optional[Card]]) -> np.ndarray:
        """Create a boolean mask of valid actions given choices.

        Args:
            choices: List of valid Card objects and/or None.

        Returns:
            Boolean array of shape (action_size,) where True = valid.
        """
        mask = np.zeros(self._action_size, dtype=bool)
        for choice in choices:
            idx = self.card_to_action(choice)
            mask[idx] = True
        return mask
