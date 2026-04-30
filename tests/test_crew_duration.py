"""Regression tests for Crew's duration cleanup.

Crew is an Action-Duration: +3 Cards on play, then top-decks itself at the
start of the next turn. Without explicit cleanup the same Crew object would
end up referenced from both ``deck`` (via the top-deck) and ``in_play``
(left over from the previous turn), and the cleanup phase would then move
the in_play copy to ``discard`` while the deck reference persists, giving
the player two Crews where there should be one.
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

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, *args, **kwargs):
        return None


def _all_cards(player: PlayerState):
    return (
        list(player.hand)
        + list(player.deck)
        + list(player.discard)
        + list(player.in_play)
        + list(player.duration)
    )


def test_crew_does_not_duplicate_after_duration_topdeck():
    state = GameState(players=[])
    state.players = [PlayerState(_NullAI())]
    state.players[0].deck = [get_card("Copper") for _ in range(5)]
    state.players[0].draw_cards(0)  # initialize hand state

    crew = Crew()
    player = state.players[0]
    player.hand = [crew] + [get_card("Copper") for _ in range(4)]
    player.in_play = []
    player.duration = []

    # Simulate the action phase placing Crew into in_play, then on_play.
    player.hand.remove(crew)
    player.in_play.append(crew)
    crew.on_play(state)

    assert crew in player.in_play, "Crew should remain in play after on_play (duration)"
    assert crew in player.duration, "Crew should be tracked as a duration"

    # End-of-turn cleanup analog: durations stay in_play. Skip the full
    # cleanup logic and just verify the on_duration step's cleanup.
    crew.on_duration(state)

    # Exactly one reference, on top of the deck.
    occurrences = sum(1 for card in _all_cards(player) if card is crew)
    assert occurrences == 1, f"Crew duplicated across zones: {occurrences}"
    assert player.deck and player.deck[-1] is crew, "Crew should be on top of deck"
    assert crew not in player.in_play
    assert crew not in player.duration


def test_crew_in_play_count_is_one_after_full_duration_cycle():
    """End-to-end: play Crew, run start-of-next-turn, ensure no zone duplicates."""
    from dominion.ai.base_ai import AI

    class _PassAI(AI):
        @property
        def name(self):
            return "pass"

        def choose_action(self, state, choices):
            return None

        def choose_treasure(self, state, choices):
            return None

        def choose_buy(self, state, choices):
            return None

        def choose_card_to_trash(self, state, choices):
            return None

    state = GameState(players=[])
    state.players = [PlayerState(_PassAI()), PlayerState(_PassAI())]
    for p in state.players:
        p.initialize()

    crew = Crew()
    player = state.players[0]
    player.hand.append(crew)

    # Play Crew via the engine action loop's mechanics.
    player.hand.remove(crew)
    player.in_play.append(crew)
    crew.on_play(state)

    # Run the cleanup-phase preserve logic (durations stay in play).
    state.handle_cleanup_phase()

    # Now the next turn's duration phase fires.
    state.current_player_index = 0
    state.handle_start_phase()

    cards = _all_cards(player)
    counts = Counter(id(c) for c in cards)
    assert counts[id(crew)] == 1, "Crew exists in exactly one zone after duration trigger"
