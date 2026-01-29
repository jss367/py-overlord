"""Tests for RLAI adapter."""

import pytest
from dominion.rl.rl_ai import RLAI
from dominion.cards.registry import get_card


class TestRLAI:
    """Tests for the RLAI class."""

    def test_name_property(self):
        """RLAI should have a configurable name."""
        ai = RLAI(name="TestBot")
        assert ai.name == "TestBot"

    def test_default_name(self):
        """RLAI should have a default name."""
        ai = RLAI()
        assert ai.name == "RLAI"

    def test_set_next_action(self):
        """RLAI should accept queued actions."""
        ai = RLAI()
        copper = get_card("Copper")
        ai.set_next_action(copper)
        assert ai._pending_action == copper

    def test_choose_action_returns_pending(self):
        """choose_action should return the pending action."""
        ai = RLAI()
        village = get_card("Village")
        ai.set_next_action(village)
        # state and choices don't matter - we return what was queued
        result = ai.choose_action(None, [village, None])
        assert result == village

    def test_choose_action_clears_pending(self):
        """choose_action should clear the pending action after use."""
        ai = RLAI()
        village = get_card("Village")
        ai.set_next_action(village)
        ai.choose_action(None, [village, None])
        assert ai._pending_action is None

    def test_choose_buy_returns_pending(self):
        """choose_buy should return the pending action."""
        ai = RLAI()
        silver = get_card("Silver")
        ai.set_next_action(silver)
        result = ai.choose_buy(None, [silver, None])
        assert result == silver

    def test_choose_treasure_returns_pending(self):
        """choose_treasure should return the pending action."""
        ai = RLAI()
        copper = get_card("Copper")
        ai.set_next_action(copper)
        result = ai.choose_treasure(None, [copper, None])
        assert result == copper

    def test_choose_card_to_trash_returns_pending(self):
        """choose_card_to_trash should return the pending action."""
        ai = RLAI()
        copper = get_card("Copper")
        ai.set_next_action(copper)
        result = ai.choose_card_to_trash(None, [copper])
        assert result == copper

    def test_none_action_allowed(self):
        """RLAI should handle None actions (pass/skip)."""
        ai = RLAI()
        ai.set_next_action(None)
        result = ai.choose_action(None, [get_card("Village"), None])
        assert result is None
