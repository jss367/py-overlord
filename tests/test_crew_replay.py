"""Crew must not duplicate itself when replayed during the same turn.

Effects like Flagship and Throne Room can play the same Crew instance more
than once on the same turn. Each play of Crew draws cards, but the duration
listing must not be added multiple times — otherwise the start-of-next-turn
duration phase iterates the same instance several times and ``on_duration``
appends the same card object to the deck more than once.
"""

from collections import Counter

from dominion.cards.plunder.crew import Crew
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _NullAI:
    name = "null"

    def __init__(self):
        self.strategy = None

    def choose_action(self, *a, **k):
        return None

    def choose_treasure(self, *a, **k):
        return None

    def choose_buy(self, *a, **k):
        return None

    def choose_card_to_trash(self, *a, **k):
        return None


def test_crew_replay_does_not_duplicate_in_duration():
    """Two play_effect calls (simulating Flagship's extra play) must not add
    Crew to player.duration twice."""
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI())]
    state.players[0].deck = [get_card("Copper") for _ in range(8)]
    crew = Crew()
    player = state.players[0]
    player.in_play.append(crew)

    crew.on_play(state)  # first play
    crew.on_play(state)  # Flagship replay

    counts = Counter(id(c) for c in player.duration)
    assert counts[id(crew)] == 1, (
        "Crew must appear in duration exactly once even after a replay; "
        f"got {counts[id(crew)]} entries"
    )


def test_crew_replay_does_not_duplicate_in_deck_after_duration():
    """If Flagship replayed Crew, the start-of-next-turn duration phase must
    still leave exactly one Crew on the deck, not two."""
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI())]
    state.players[0].deck = [get_card("Copper") for _ in range(8)]
    crew = Crew()
    player = state.players[0]
    player.in_play.append(crew)

    crew.on_play(state)
    crew.on_play(state)

    # Pretend the engine just kicked the duration phase: iterate a snapshot.
    for entry in list(player.duration):
        entry.on_duration(state)

    crew_count_in_deck = sum(1 for c in player.deck if c is crew)
    assert crew_count_in_deck == 1, (
        f"Crew should appear on the deck exactly once after duration; got {crew_count_in_deck}"
    )
    assert crew not in player.duration
    assert crew not in player.in_play
