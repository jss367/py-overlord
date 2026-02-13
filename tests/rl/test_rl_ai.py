"""Tests for RLAI adapter."""

import threading
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

    def test_has_queues(self):
        """RLAI should have choice and action queues."""
        ai = RLAI()
        assert ai.choice_queue is not None
        assert ai.action_queue is not None

    def test_choose_action_puts_choices_and_waits(self):
        """choose_action should put choices on queue and return action from action_queue."""
        ai = RLAI()
        village = get_card("Village")
        choices = [village, None]

        result = [None]

        def call_choose():
            result[0] = ai.choose_action(None, choices)

        t = threading.Thread(target=call_choose)
        t.start()

        # RLAI should have put choices on the queue
        decision_type, state, received_choices = ai.choice_queue.get(timeout=2)
        assert decision_type == "action"
        assert received_choices == choices

        # Provide the action
        ai.action_queue.put(village)
        t.join(timeout=2)

        assert result[0] == village

    def test_choose_buy_puts_choices(self):
        """choose_buy should communicate via queues."""
        ai = RLAI()
        silver = get_card("Silver")
        choices = [silver, None]

        result = [None]

        def call_choose():
            result[0] = ai.choose_buy(None, choices)

        t = threading.Thread(target=call_choose)
        t.start()

        decision_type, _, _ = ai.choice_queue.get(timeout=2)
        assert decision_type == "buy"
        ai.action_queue.put(silver)
        t.join(timeout=2)

        assert result[0] == silver

    def test_choose_treasure_puts_choices(self):
        """choose_treasure should communicate via queues."""
        ai = RLAI()
        copper = get_card("Copper")

        result = [None]

        def call_choose():
            result[0] = ai.choose_treasure(None, [copper, None])

        t = threading.Thread(target=call_choose)
        t.start()

        decision_type, _, _ = ai.choice_queue.get(timeout=2)
        assert decision_type == "treasure"
        ai.action_queue.put(copper)
        t.join(timeout=2)

        assert result[0] == copper

    def test_none_action_allowed(self):
        """RLAI should handle None actions (pass/skip)."""
        ai = RLAI()

        result = [None]

        def call_choose():
            result[0] = ai.choose_action(None, [get_card("Village"), None])

        t = threading.Thread(target=call_choose)
        t.start()

        ai.choice_queue.get(timeout=2)
        ai.action_queue.put(None)
        t.join(timeout=2)

        assert result[0] is None
