"""Student top-decks itself when its trashed card is a Treasure.

Per Allies rules, Student says: "+1 Action. +1 Favor. Trash a card from your
hand. If it's a Treasure, put this onto your deck." The previous implementation
only granted the +1 Favor and left Student in the normal play→discard flow,
which silently dropped the recycle effect on Treasure-trash turns.
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState


class _TrashCopperAI:
    """AI that always picks Copper from a trash prompt and is a no-op otherwise."""

    name = "trash-copper"

    def __init__(self):
        self.strategy = None

    def choose_action(self, *args, **kwargs):
        return None

    def choose_treasure(self, *args, **kwargs):
        return None

    def choose_buy(self, *args, **kwargs):
        return None

    def choose_card_to_trash(self, _state, choices):
        for c in choices:
            if c.name == "Copper":
                return c
        return None


class _TrashEstateAI(_TrashCopperAI):
    name = "trash-estate"

    def choose_card_to_trash(self, _state, choices):
        for c in choices:
            if c.name == "Estate":
                return c
        return None


def _new_state(ai_cls) -> tuple[GameState, PlayerState]:
    state = GameState(players=[])
    state.players = [PlayerState(ai_cls())]
    state.setup_supply([get_card("Student")])
    return state, state.players[0]


def test_student_top_decks_itself_after_trashing_a_treasure():
    state, player = _new_state(_TrashCopperAI)
    student = get_card("Student")
    player.hand = [get_card("Copper")]
    player.in_play = [student]

    student.play_effect(state)

    assert get_card("Copper") not in player.hand
    # Student should now be on top of the deck (end of list = top).
    assert player.deck and player.deck[-1] is student, (
        "Student should be moved to the top of the deck after trashing a Treasure"
    )
    assert student not in player.in_play
    # And +1 Favor was awarded for the Treasure trash (on top of the Liaison +1).
    assert player.favors == 2


def test_student_stays_in_play_when_trashing_a_non_treasure():
    state, player = _new_state(_TrashEstateAI)
    student = get_card("Student")
    player.hand = [get_card("Estate")]
    player.in_play = [student]

    student.play_effect(state)

    assert student in player.in_play, (
        "Student should stay in play when the trashed card was not a Treasure"
    )
    assert student not in player.deck
    # Only the Liaison favor was awarded.
    assert player.favors == 1
