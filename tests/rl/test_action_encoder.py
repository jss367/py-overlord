"""Tests for action encoder."""

import numpy as np
import pytest
from dominion.rl.action_encoder import ActionEncoder
from dominion.rl.state_encoder import PHASE1_KINGDOM
from dominion.cards.registry import get_card


class TestActionEncoder:
    """Tests for ActionEncoder."""

    def test_initialization(self):
        """ActionEncoder should initialize with kingdom cards."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        assert encoder.action_size > 0

    def test_action_size_includes_pass(self):
        """Action space should include a pass/none action."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        # base cards + kingdom cards + 1 for pass
        expected = 7 + len(PHASE1_KINGDOM) + 1
        assert encoder.action_size == expected

    def test_encode_card_to_index(self):
        """Should encode a card to its index."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        copper = get_card("Copper")
        idx = encoder.card_to_action(copper)
        assert isinstance(idx, int)
        assert 0 <= idx < encoder.action_size

    def test_encode_none_to_index(self):
        """Should encode None (pass) to the pass index."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        idx = encoder.card_to_action(None)
        assert idx == encoder.pass_action_index

    def test_decode_index_to_card(self):
        """Should decode an index back to a card."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        copper = get_card("Copper")
        idx = encoder.card_to_action(copper)
        decoded = encoder.action_to_card(idx)
        assert decoded.name == "Copper"

    def test_decode_pass_index(self):
        """Should decode pass index to None."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        decoded = encoder.action_to_card(encoder.pass_action_index)
        assert decoded is None

    def test_roundtrip_all_cards(self):
        """All cards should roundtrip correctly."""
        encoder = ActionEncoder(PHASE1_KINGDOM)
        all_cards = ["Copper", "Silver", "Gold", "Estate", "Duchy", "Province", "Curse"] + list(PHASE1_KINGDOM)

        for card_name in all_cards:
            card = get_card(card_name)
            idx = encoder.card_to_action(card)
            decoded = encoder.action_to_card(idx)
            assert decoded.name == card_name

    def test_get_valid_action_mask(self):
        """Should create mask for valid actions."""
        encoder = ActionEncoder(PHASE1_KINGDOM)

        copper = get_card("Copper")
        silver = get_card("Silver")
        choices = [copper, silver, None]

        mask = encoder.get_action_mask(choices)

        assert isinstance(mask, np.ndarray)
        assert mask.shape == (encoder.action_size,)
        assert mask.dtype == bool

        # Copper, Silver, and pass should be valid
        assert mask[encoder.card_to_action(copper)] == True
        assert mask[encoder.card_to_action(silver)] == True
        assert mask[encoder.pass_action_index] == True

        # Gold should be invalid
        gold = get_card("Gold")
        assert mask[encoder.card_to_action(gold)] == False

    def test_mask_valid_actions_from_choices(self):
        """Mask should reflect exactly the available choices."""
        encoder = ActionEncoder(PHASE1_KINGDOM)

        village = get_card("Village")
        choices = [village]  # No pass option

        mask = encoder.get_action_mask(choices)

        assert mask[encoder.card_to_action(village)] == True
        assert mask[encoder.pass_action_index] == False
        assert mask.sum() == 1
