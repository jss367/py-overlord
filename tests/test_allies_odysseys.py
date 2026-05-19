"""Focused tests for Allies Odysseys split-pile cards."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class PlayFirstAI(DummyAI):
    def choose_action(self, state, choices):
        for choice in choices:
            if choice is not None:
                return choice
        return None

    def choose_treasure(self, state, choices):
        for choice in choices:
            if choice is not None:
                return choice
        return None


def _make_state() -> tuple[GameState, PlayerState, PlayerState]:
    players = [PlayerState(DummyAI()), PlayerState(DummyAI())]
    state = GameState(players=players)
    state.supply = {"Estate": 8, "Silver": 10}
    state.current_player_index = 0
    for player in players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.in_play = []
        player.duration = []
    return state, players[0], players[1]


def _play_card(state: GameState, player: PlayerState, card) -> None:
    if card in player.hand:
        player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


def test_voyage_grants_extra_turn_with_three_card_play_limit():
    state, player, opponent = _make_state()
    voyage = get_card("Voyage")
    player.hand = [voyage]
    player.deck = [get_card("Copper") for _ in range(5)]

    _play_card(state, player, voyage)

    assert player.outpost_pending is False
    assert player.voyage_extra_turn_pending is True
    assert state.extra_turn is True
    assert player.mission_no_buy_turn is False
    player.coins = 8
    assert state._get_affordable_cards(player)

    state.handle_cleanup_phase()

    assert state.current_player is player
    assert state.current_player is not opponent
    assert len(player.hand) == 5
    assert player.outpost_pending is False
    assert player.took_extra_turn_last_turn is True

    state.handle_start_phase()
    player.coins = 8

    assert player.mission_no_buy_turn is False
    assert player.voyage_cards_from_hand_remaining == 3
    assert state._get_affordable_cards(player)


def test_voyage_extra_turn_limits_cards_played_from_hand():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    player.voyage_extra_turn_pending = True
    player.hand = [
        get_card("Village"),
        get_card("Village"),
        get_card("Village"),
        get_card("Village"),
    ]

    state.handle_start_phase()
    state.handle_action_phase()

    assert len(player.in_play) == 3
    assert len(player.hand) == 1
    assert player.voyage_cards_from_hand_remaining == 0


def test_voyage_limit_blocks_inspiring_extra_play():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    state.pile_traits["Village"] = "Inspiring"
    smithy = get_card("Smithy")
    player.hand = [smithy]
    player.voyage_cards_from_hand_remaining = 0

    state._maybe_inspiring_extra_play(player, get_card("Village"))

    assert player.hand == [smithy]
    assert player.in_play == []


def test_voyage_limit_counts_inspiring_extra_play():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    state.pile_traits["Village"] = "Inspiring"
    smithy = get_card("Smithy")
    player.hand = [smithy]
    player.voyage_cards_from_hand_remaining = 1

    state._maybe_inspiring_extra_play(player, get_card("Village"))

    assert player.hand == []
    assert player.in_play == [smithy]
    assert player.voyage_cards_from_hand_remaining == 0


def test_voyage_limit_blocks_throne_room_play_from_hand():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    throne_room = get_card("Throne Room")
    smithy = get_card("Smithy")
    player.hand = [smithy]
    player.in_play = [throne_room]
    player.voyage_cards_from_hand_remaining = 0

    throne_room.on_play(state)

    assert player.hand == [smithy]
    assert player.in_play == [throne_room]


def test_voyage_limit_counts_throne_room_play_from_hand_once():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    throne_room = get_card("Throne Room")
    smithy = get_card("Smithy")
    player.hand = [smithy]
    player.in_play = [throne_room]
    player.deck = [get_card("Copper") for _ in range(6)]
    player.voyage_cards_from_hand_remaining = 1

    throne_room.on_play(state)

    assert smithy not in player.hand
    assert smithy in player.in_play
    assert player.voyage_cards_from_hand_remaining == 0
    assert len(player.hand) == 6


def test_voyage_limit_blocks_crown_treasure_play_from_hand():
    state, player, _opponent = _make_state()
    player.ai = PlayFirstAI()
    crown = get_card("Crown")
    silver = get_card("Silver")
    state.phase = "treasure"
    player.hand = [silver]
    player.in_play = [crown]
    player.voyage_cards_from_hand_remaining = 0

    crown.on_play(state)

    assert player.hand == [silver]
    assert player.in_play == [crown]


def test_voyage_does_not_grant_third_consecutive_turn():
    state, player, _opponent = _make_state()
    voyage = get_card("Voyage")
    player.took_extra_turn_last_turn = True
    player.hand = [voyage]

    _play_card(state, player, voyage)

    assert player.outpost_pending is False
    assert getattr(player, "voyage_extra_turn_pending", False) is False
    assert state.extra_turn is False
    assert voyage in player.duration
