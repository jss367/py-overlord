"""Tests for newly implemented Base and Intrigue cards."""

from __future__ import annotations

from pathlib import Path

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI


def test_militia_forces_discards():
    attacker_ai = ChooseFirstActionAI()
    defender_ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([attacker_ai, defender_ai], [get_card("Militia")])

    player = state.players[0]
    opponent = state.players[1]

    militia = get_card("Militia")
    player.hand = [militia]
    player.actions = 1

    opponent.hand = [
        get_card("Estate"),
        get_card("Copper"),
        get_card("Silver"),
        get_card("Gold"),
        get_card("Village"),
    ]

    militia.on_play(state)

    assert player.coins == 2
    assert len(opponent.hand) == 3
    assert len(opponent.discard) >= 1


def test_adventurer_finds_two_treasures():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Adventurer")])

    player = state.players[0]
    adventurer = get_card("Adventurer")

    player.hand = []
    player.deck = [
        get_card("Estate"),
        get_card("Copper"),
        get_card("Silver"),
        get_card("Estate"),
    ]
    player.discard = []

    adventurer.on_play(state)

    treasures = [card for card in player.hand if card.is_treasure]
    assert len(treasures) == 2
    names = {card.name for card in treasures}
    assert {"Copper", "Silver"} <= names
    assert any(card.name == "Estate" for card in player.discard)


def test_throne_room_plays_action_twice():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Throne Room"), get_card("Smithy")])

    player = state.players[0]
    throne_room = get_card("Throne Room")
    smithy = get_card("Smithy")

    player.hand = [smithy]
    player.deck = [get_card("Copper") for _ in range(6)]
    player.discard = []

    throne_room.on_play(state)

    assert sum(1 for card in player.in_play if card.name == "Smithy") == 1
    assert len(player.deck) == 0
    assert len([card for card in player.hand if card.name == "Copper"]) == 6


def test_sentry_processes_revealed_cards():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Sentry")])

    player = state.players[0]
    sentry = get_card("Sentry")

    player.hand = []
    player.deck = [
        get_card("Silver"),
        get_card("Estate"),
        get_card("Curse"),
        get_card("Copper"),
    ]
    player.discard = []
    state.trash = []

    sentry.on_play(state)

    assert any(card.name == "Curse" for card in state.trash)
    assert any(card.name == "Estate" for card in state.trash + player.discard)
    assert any(card.name == "Copper" for card in player.hand)


def test_remodel_trashes_and_gains_upgrade():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Remodel")])

    player = state.players[0]
    remodel = get_card("Remodel")

    estate = get_card("Estate")
    player.hand = [estate]
    state.trash = []

    remodel.on_play(state)

    assert any(card.name == "Estate" for card in state.trash)
    assert player.discard
    gained = player.discard[-1]
    assert gained.cost.coins <= estate.cost.coins + 2
    assert gained.name != "Estate"


def test_steward_prefers_trashing_junk():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])

    player = state.players[0]
    steward = get_card("Steward")

    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    state.trash = []

    steward.on_play(state)

    trashed_names = [card.name for card in state.trash]
    assert "Copper" in trashed_names
    assert "Estate" in trashed_names


def test_steward_adds_coins_when_no_junk():
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])

    player = state.players[0]
    steward = get_card("Steward")

    player.hand = [get_card("Silver")]
    player.coins = 0

    steward.on_play(state)

    assert player.coins == 2


def test_kingdom_configurations_initialize():
    config_path = Path("kingdom_config.yaml")
    contents = config_path.read_text(encoding="utf-8")

    default_kingdom, alternative_kingdoms = _parse_kingdom_config(contents)

    kingdoms = [default_kingdom] + list(alternative_kingdoms.values())
    assert kingdoms, "Expected at least one kingdom to test"

    for kingdom in kingdoms:
        ais = [ChooseFirstActionAI(), ChooseFirstActionAI()]
        state = GameState(players=[])
        cards = [get_card(name) for name in kingdom]
        state.initialize_game(ais, cards)


def _parse_kingdom_config(text: str) -> tuple[list[str], dict[str, list[str]]]:
    default_cards: list[str] = []
    alternatives: dict[str, list[str]] = {}
    current_list: list[str] | None = None
    current_alt: str | None = None
    in_alternatives = False

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        if not raw_line.startswith(" "):
            current_list = None
            current_alt = None
            in_alternatives = raw_line.strip().startswith("alternative_kingdoms:")
            if raw_line.strip().startswith("kingdom_cards:"):
                current_list = default_cards
                in_alternatives = False
            continue

        if not in_alternatives and raw_line.strip().startswith("- "):
            card_name = raw_line.strip()[2:].strip().strip('"')
            default_cards.append(card_name)
            continue

        if in_alternatives:
            if raw_line.startswith("  ") and not raw_line.startswith("    "):
                # Name of the alternative kingdom
                current_alt = raw_line.strip()[:-1]
                alternatives[current_alt] = []
                current_list = alternatives[current_alt]
                continue

            if raw_line.strip().startswith("- ") and current_list is not None:
                card_name = raw_line.strip()[2:].strip().strip('"')
                current_list.append(card_name)

    return default_cards, alternatives
