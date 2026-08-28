"""Tests for declarative card capabilities (dominion.analysis.card_capabilities)."""

from __future__ import annotations

from dominion.analysis.card_capabilities import capabilities_for, kingdom_capabilities


def test_static_stats_pass_through():
    caps = capabilities_for("Workers' Village")
    assert caps is not None
    assert caps.actions == 2
    assert caps.draw == 1.0
    assert caps.buys == 1
    assert caps.is_action and not caps.is_treasure


def test_dynamic_draw_overrides_zero_stats():
    """Magnate's stats are all zero (its draw is computed in play_effect);
    the override table must expose it as a real draw source."""
    caps = capabilities_for("Magnate")
    assert caps is not None
    assert caps.draw >= 2.0
    assert caps.is_action


def test_dynamic_coins_override():
    caps = capabilities_for("Bank")
    assert caps is not None
    assert caps.is_treasure
    assert caps.coins >= 2.0


def test_multiplier_flag():
    for name in ("Throne Room", "King's Court"):
        caps = capabilities_for(name)
        assert caps is not None and caps.is_multiplier, name


def test_gainer_and_trasher_flags():
    assert capabilities_for("Workshop").is_gainer
    assert capabilities_for("Anvil").is_gainer
    expand = capabilities_for("Expand")
    assert expand.is_gainer and expand.is_trasher
    assert capabilities_for("Chapel").is_trasher


def test_attack_derived_from_types():
    assert capabilities_for("Witch").is_attack
    assert not capabilities_for("Smithy").is_attack


def test_unknown_card_returns_none():
    assert capabilities_for("Not A Card") is None


def test_kingdom_capabilities_skips_unknown():
    caps = kingdom_capabilities(["Village", "Not A Card", "Smithy"])
    assert set(caps) == {"Village", "Smithy"}
