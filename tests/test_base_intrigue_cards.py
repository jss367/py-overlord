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
    player.actions = 0  # no action to spend a draw on → +$2 is best

    steward.on_play(state)

    assert player.coins == 2


def test_steward_never_trashes_treasure_to_fill_quota():
    """Steward is "trash up to 2" — even in trash mode it must never
    trash a good card (Gold/Silver/Province) just to reach a count of
    two. Trash mode is forced here to isolate the trash routine from
    the mode heuristic."""

    class TrashModeAI(ChooseFirstActionAI):
        def choose_steward_mode(self, state, player):
            return "trash"

    ai = TrashModeAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])

    player = state.players[0]
    player.hand = [
        get_card("Copper"),
        get_card("Gold"),
        get_card("Gold"),
        get_card("Gold"),
        get_card("Gold"),
    ]
    state.trash = []

    get_card("Steward").on_play(state)

    trashed = [c.name for c in state.trash]
    assert "Gold" not in trashed
    assert "Silver" not in trashed
    # The single junk card is still removed.
    assert trashed == ["Copper"]
    assert sum(1 for c in player.hand if c.name == "Gold") == 4


def test_steward_mode_choice_is_delegated_to_ai():
    """The controlling AI decides Steward's mode. An AI that asks for
    +2 Cards must get cards even when junk is in hand (no forced trash)."""

    class CardsModeAI(ChooseFirstActionAI):
        def choose_steward_mode(self, state, player):
            return "cards"

    ai = CardsModeAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])

    player = state.players[0]
    player.hand = [get_card("Copper"), get_card("Estate")]
    player.coins = 0
    state.trash = []

    get_card("Steward").on_play(state)

    assert state.trash == []
    assert player.coins == 0
    assert len(player.hand) == 4  # drew 2


def test_throne_room_steward_does_not_trash_treasure():
    """Doubling Steward (Throne Room) in trash mode must still never
    trash treasure."""

    class TrashModeAI(ChooseFirstActionAI):
        def choose_steward_mode(self, state, player):
            return "trash"

    ai = TrashModeAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])

    player = state.players[0]
    player.hand = [
        get_card("Copper"),
        get_card("Gold"),
        get_card("Gold"),
        get_card("Gold"),
    ]
    state.trash = []

    steward = get_card("Steward")
    steward.on_play(state)
    steward.on_play(state)  # second play simulates Throne Room

    trashed = [c.name for c in state.trash]
    assert "Gold" not in trashed
    assert trashed == ["Copper"]


def _steward_mode(hand, actions, coins):
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Steward")])
    player = state.players[0]
    player.hand = [get_card(n) for n in hand]
    player.actions = actions
    player.coins = coins
    return ai.choose_steward_mode(state, player)


def test_steward_mode_trashes_only_with_two_or_more_junk():
    # 2+ junk in hand: trimming a full pair is worth it even mid-engine.
    assert _steward_mode(["Copper", "Estate", "Gold"], actions=3, coins=0) == "trash"


def test_steward_mode_prefers_cards_with_spare_action_over_lone_junk():
    # Only one junk card: don't waste Steward half-trashing — if there is
    # an action still to play, draw to fuel it instead.
    assert _steward_mode(["Copper", "Silver", "Gold"], actions=1, coins=0) == "cards"


def test_steward_mode_prefers_cards_over_coins_with_spare_action():
    # No junk, but an action remains: +2 Cards beats +$2.
    assert _steward_mode(["Silver", "Gold"], actions=1, coins=0) == "cards"


def test_steward_mode_lone_junk_no_action_poor_takes_coins():
    # One junk, no action to use a draw, and poor: +$2 over a half-trash.
    assert _steward_mode(["Copper", "Silver"], actions=0, coins=1) == "coins"


def test_steward_mode_rich_clean_no_action_draws():
    # No junk, no action, already rich: dig for a bigger buy.
    assert _steward_mode(["Gold", "Gold"], actions=0, coins=6) == "cards"


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
