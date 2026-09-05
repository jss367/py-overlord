"""Ways are offered on indirect plays too.

Menagerie: "when you play an Action card, you may instead follow the Way's
instructions". That covers every play, not just the action-phase loop —
Throne Room replays (each one independently), cards Vassal plays, and
off-turn Reaction plays (Sheepdog, Trail). The offer lives in
``GameState.play_action_indirectly`` so every caller gets it.
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.ways.registry import get_way
from tests.utils import ChooseFirstActionAI


class ScriptedWayAI(ChooseFirstActionAI):
    """Answers ``choose_way`` from a per-card script and records every offer."""

    def __init__(self, script: dict[str, list[str | None]] | None = None):
        super().__init__()
        self.script = {name: list(picks) for name, picks in (script or {}).items()}
        self.offers: list[str] = []

    def choose_way(self, state, card, ways):
        self.offers.append(card.name)
        queue = self.script.get(card.name)
        if not queue:
            return None
        wanted = queue.pop(0)
        for way in ways:
            if way is not None and way.name == wanted:
                return way
        return None


def _game(kingdom, way_names, ais):
    state = GameState(players=[])
    state.initialize_game(
        ais,
        [get_card(name) for name in kingdom],
        ways=[get_way(name) for name in way_names],
    )
    for player in state.players:
        player.hand = []
        player.deck = []
        player.discard = []
        player.in_play = []
        player.actions = 0
        player.coins = 0
    return state


def test_throne_room_offers_a_way_on_each_replay_independently():
    # First Smithy play uses Way of the Ox (+2 Actions), second declines and
    # draws its usual 3 cards.
    ai = ScriptedWayAI({"Smithy": ["Way of the Ox", None]})
    state = _game(["Throne Room", "Smithy"], ["Way of the Ox"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    p1.hand = [get_card("Throne Room"), get_card("Smithy")]
    p1.deck = [get_card("Copper") for _ in range(10)]
    p1.actions = 1
    state.phase = "action"

    state.handle_action_phase()

    assert ai.offers == ["Throne Room", "Smithy", "Smithy"]
    assert p1.actions == 2
    assert len(p1.hand) == 3


def test_vassal_offers_a_way_for_the_card_it_plays():
    ai = ScriptedWayAI({"Village": ["Way of the Ox"]})
    state = _game(["Vassal", "Village"], ["Way of the Ox"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    p1.hand = [get_card("Vassal")]
    p1.deck = [get_card("Copper"), get_card("Village")]  # top of deck is last
    p1.actions = 1
    state.phase = "action"

    state.handle_action_phase()

    assert ai.offers == ["Vassal", "Village"]
    assert p1.coins == 2  # Vassal itself resolved normally
    assert p1.actions == 2  # Village as Ox: +2 Actions, no card drawn
    assert p1.hand == []
    assert any(card.name == "Village" for card in p1.in_play)


def test_off_turn_sheepdog_reaction_offers_a_way_to_its_owner():
    p2_ai = ScriptedWayAI({"Sheepdog": ["Way of the Ox"]})
    state = _game(["Sheepdog"], ["Way of the Ox"], [ChooseFirstActionAI(), p2_ai])
    p1, p2 = state.players
    assert state.current_player is p1
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Copper") for _ in range(3)]

    state.gain_card(p2, get_card("Silver"))

    assert p2_ai.offers == ["Sheepdog"]
    assert p2.actions == 2  # Ox applied to the reactor, not the turn player
    assert p2.hand == []  # Sheepdog's +2 Cards were replaced
    assert p1.actions == 0
    assert p1.hand == []
    assert state.current_player is p1


def test_off_turn_trail_reaction_resolves_for_its_owner():
    # Regression: Trail used to hand-roll its play and resolve for the turn
    # player, so an opponent's Militia discarding your Trail drew them a card.
    state = _game(["Trail"], [], [ChooseFirstActionAI(), ChooseFirstActionAI()])
    p1, p2 = state.players
    trail = get_card("Trail")
    p2.hand = [trail]
    p2.deck = [get_card("Copper")]
    p2.hand.remove(trail)

    state.discard_card(p2, trail)

    assert trail in p2.in_play
    assert p2.actions == 1
    assert len(p2.hand) == 1
    assert p1.actions == 0
    assert p1.hand == []
    assert state.current_player is p1


def test_trail_gain_reaction_still_offers_a_way():
    ai = ScriptedWayAI({"Trail": ["Way of the Ox"]})
    state = _game(["Trail"], ["Way of the Ox"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    p1.deck = [get_card("Copper")]

    gained = state.gain_card(p1, get_card("Trail"))

    assert ai.offers == ["Trail"]
    assert gained in p1.in_play
    assert p1.actions == 2
    assert p1.hand == []
    assert p1.actions_played == 1


def test_trail_reaction_fires_ally_play_hooks_when_using_a_way():
    """Trail's old hand-rolled path skipped the Ally hooks on a Way play; the
    shared helper fires them for every play."""
    ai = ScriptedWayAI({"Trail": ["Way of the Ox"]})
    state = _game(["Trail"], ["Way of the Ox"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    seen: list[str] = []

    class RecordingAlly:
        def on_play_card(self, game_state, player, card):
            seen.append(card.name)

    state.allies = [RecordingAlly()]

    state.gain_card(p1, get_card("Trail"))

    assert seen == ["Trail"]


def test_riverboat_virtual_play_keeps_the_card_set_aside_under_a_moving_way():
    """Riverboat plays its set-aside card in place ("it stays set aside, even
    if it has instructions on it that would move it"). The play is still a
    play, so a Way is offered; a Way that would move the card — Turtle here
    — finds it is not in play and leaves it set aside instead of stashing it."""
    ai = ScriptedWayAI({"Village": ["Way of the Turtle"]})
    state = _game(["Riverboat", "Village"], ["Way of the Turtle"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    village = get_card("Village")
    state.riverboat_set_aside = village
    riverboat = get_card("Riverboat")
    riverboat.duration_persistent = True
    p1.duration = [riverboat]
    p1.deck = [get_card("Copper")]

    riverboat.on_duration(state)

    assert ai.offers == ["Village"]
    assert p1.actions == 0  # Village's own instructions were replaced by the Way
    assert p1.hand == []
    assert state.riverboat_set_aside is village
    assert village not in p1.in_play
    assert not getattr(p1, "turtle_set_aside", [])
    assert riverboat.duration_persistent is False


def _throne_room_smithy(ai, way_names):
    state = _game(["Throne Room", "Smithy"], way_names, [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    smithy = get_card("Smithy")
    p1.hand = [get_card("Throne Room"), smithy]
    p1.deck = [get_card("Copper") for _ in range(10)]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    return state, p1, smithy


def test_throne_room_still_offers_a_way_after_turtle_moved_the_card():
    """A Throne-Roomed card that leaves play is still played again, and that
    second play gets its own Way offer even though the card is no longer in
    play."""
    ai = ScriptedWayAI({"Smithy": ["Way of the Turtle", "Way of the Ox"]})
    state, p1, smithy = _throne_room_smithy(ai, ["Way of the Turtle", "Way of the Ox"])

    assert ai.offers == ["Throne Room", "Smithy", "Smithy"]
    assert p1.turtle_set_aside == [smithy]
    assert smithy not in p1.in_play
    assert p1.actions == 2  # Ox on the second play
    assert p1.hand == []  # Smithy never drew


def test_throne_room_turtle_twice_stashes_the_card_once():
    ai = ScriptedWayAI({"Smithy": ["Way of the Turtle", "Way of the Turtle"]})
    state, p1, smithy = _throne_room_smithy(ai, ["Way of the Turtle"])

    assert ai.offers == ["Throne Room", "Smithy", "Smithy"]
    assert p1.turtle_set_aside == [smithy]
    assert smithy not in p1.in_play
    assert p1.hand == []


def _captain_plays_from_supply(ai, way_names):
    state = _game(["Captain", "Smithy"], way_names, [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    captain = get_card("Captain")
    p1.duration = [captain]
    p1.deck = [get_card("Copper") for _ in range(5)]
    supply_before = dict(state.supply)
    captain.on_duration(state)
    return state, p1, supply_before


def test_captain_supply_play_under_turtle_stashes_nothing():
    """Captain plays a Supply card "leaving it there"; the proxy is a virtual
    play and Way of the Turtle must not stash a card the player never had."""
    ai = ScriptedWayAI({"Smithy": ["Way of the Turtle"]})
    state, p1, supply_before = _captain_plays_from_supply(ai, ["Way of the Turtle"])

    assert ai.offers == ["Smithy"]
    assert not getattr(p1, "turtle_set_aside", [])
    assert all(card.name != "Smithy" for card in p1.in_play)
    assert state.supply == supply_before
    assert p1.hand == []  # Smithy's draw was replaced by the Way


def test_captain_supply_play_under_butterfly_returns_and_gains_nothing():
    """Butterfly: "You may return this to its pile. If you do, gain a card
    costing exactly $1 more." The Supply proxy cannot be returned, so the
    Smithy pile stays put and no $5 card (Duchy is available) is gained."""
    ai = ScriptedWayAI({"Smithy": ["Way of the Butterfly"]})
    state, p1, supply_before = _captain_plays_from_supply(ai, ["Way of the Butterfly"])

    assert ai.offers == ["Smithy"]
    assert state.supply == supply_before
    assert p1.discard == []
    assert p1.hand == []


def test_way_played_indirect_attack_still_fires_urchin():
    """Vassal plays Militia via Way of the Ox. A Way replaces the card's
    instructions, not the play, so an Urchin in play still reacts to the
    Attack play: it is trashed and a Mercenary gained."""
    ai = ScriptedWayAI({"Militia": ["Way of the Ox"]})
    state = _game(
        ["Vassal", "Militia", "Urchin"], ["Way of the Ox"], [ai, ChooseFirstActionAI()]
    )
    p1, p2 = state.players
    urchin = get_card("Urchin")
    p1.in_play = [urchin]
    p1.hand = [get_card("Vassal")]
    p1.deck = [get_card("Copper"), get_card("Militia")]  # top of deck is last
    p1.actions = 1
    p2.hand = [get_card("Copper") for _ in range(5)]
    state.phase = "action"

    state.handle_action_phase()

    assert ai.offers == ["Vassal", "Militia"]
    assert urchin not in p1.in_play
    assert urchin in state.trash
    assert any(card.name == "Mercenary" for card in p1.discard)
    assert state.supply["Mercenary"] == 9
    assert len(p2.hand) == 5  # Militia's own attack was replaced by the Way
    assert p1.actions == 2
