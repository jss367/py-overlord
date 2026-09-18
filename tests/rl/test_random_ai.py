"""Tests for RandomAI opponent."""

import random
import pytest
from dominion.rl.random_ai import RandomAI
from dominion.cards.registry import get_card


class TestRandomAI:
    """Tests for RandomAI."""

    def test_name_property(self):
        """RandomAI should have a name."""
        ai = RandomAI()
        assert ai.name == "RandomAI"

    def test_choose_action_returns_valid_choice(self):
        """choose_action should return one of the choices."""
        random.seed(42)
        ai = RandomAI()
        village = get_card("Village")
        smithy = get_card("Smithy")
        choices = [village, smithy, None]

        result = ai.choose_action(None, choices)
        assert result in choices

    def test_choose_action_can_return_none(self):
        """choose_action should sometimes return None (pass)."""
        ai = RandomAI()
        village = get_card("Village")
        choices = [village, None]

        # Run many times, should get None at least once
        results = [ai.choose_action(None, choices) for _ in range(100)]
        assert None in results

    def test_choose_buy_returns_valid_choice(self):
        """choose_buy should return one of the choices."""
        random.seed(42)
        ai = RandomAI()
        silver = get_card("Silver")
        choices = [silver, None]

        result = ai.choose_buy(None, choices)
        assert result in choices

    def test_choose_treasure_returns_valid_choice(self):
        """choose_treasure should return one of the choices."""
        random.seed(42)
        ai = RandomAI()
        copper = get_card("Copper")
        choices = [copper, None]

        result = ai.choose_treasure(None, choices)
        assert result in choices

    def test_choose_card_to_trash_returns_valid_choice(self):
        """Mandatory trashing cannot invent a pass option."""
        random.seed(42)
        ai = RandomAI()
        copper = get_card("Copper")
        estate = get_card("Estate")
        choices = [copper, estate]

        result = ai.choose_card_to_trash(None, choices)
        assert result in choices

    def test_trash_only_passes_when_effect_offers_none(self, monkeypatch):
        monkeypatch.setattr(random, "choice", lambda choices: choices[-1])
        ai = RandomAI()
        gold = get_card("Gold")
        assert ai.choose_card_to_trash(None, [gold]) is gold
        assert ai.choose_card_to_trash(None, [gold, None]) is None
