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


def _game(kingdom, way_names, ais, projects=None):
    state = GameState(players=[])
    state.initialize_game(
        ais,
        [get_card(name) for name in kingdom],
        ways=[get_way(name) for name in way_names],
        projects=projects,
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


def test_frog_on_a_virtual_play_gives_the_action_but_leaves_no_marker():
    """Way of the Frog: "+1 Action. When you discard this from play this turn,
    put it onto your deck." A virtual play (Necromancer's trashed card here,
    played from the trash without entering play) still gets the +1 Action,
    but the topdeck clause cannot apply to a card that is not in play. If the
    marker were set anyway, cleanup would never clear it (it only clears
    markers on cards in play) and the instance would be topdecked on a later
    turn."""
    ai = ScriptedWayAI({"Smithy": ["Way of the Frog"]})
    state = _game(["Smithy"], ["Way of the Frog"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    smithy = get_card("Smithy")
    state.trash = [smithy]
    p1.deck = [get_card("Copper") for _ in range(3)]

    state.play_action_indirectly(p1, smithy)

    assert ai.offers == ["Smithy"]
    assert p1.actions == 1
    assert p1.hand == []  # Smithy's draw was replaced by the Way
    assert smithy not in p1.in_play
    assert getattr(smithy, "_frog_topdeck", False) is False


def test_off_turn_seal_expires_when_the_turn_players_turn_ends():
    """Way of the Seal: "+$1. This turn, when you gain a card, put it onto
    your deck." Played off-turn (p2's Sheepdog during p1's turn) it applies to
    the reactor, and "this turn" is p1's turn, so p1's cleanup must clear
    p2's flag too — otherwise it would linger into other players' turns."""
    p2_ai = ScriptedWayAI({"Sheepdog": ["Way of the Seal"]})
    state = _game(["Sheepdog"], ["Way of the Seal"], [ChooseFirstActionAI(), p2_ai])
    p1, p2 = state.players
    assert state.current_player is p1
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Copper") for _ in range(3)]

    state.gain_card(p2, get_card("Silver"))

    assert p2_ai.offers == ["Sheepdog"]
    assert p2.coins == 1  # Seal's +$1 went to the reactor
    assert p1.coins == 0
    assert p2.way_of_seal_active is True
    assert p1.way_of_seal_active is False

    state.handle_cleanup_phase()

    assert p2.way_of_seal_active is False
    assert p1.way_of_seal_active is False


def test_off_turn_way_resources_expire_when_the_turn_players_turn_ends():
    """+Actions/+$/+Buys granted to a reactor off-turn (p2's Sheepdog via Way
    of the Ox during p1's turn) are meaningless outside their own turn and
    vanish when the current turn ends; only cards drawn persist. Cleanup must
    therefore reset every player's resources, not just the turn player's, or
    p2 would start their next turn with the banked Actions."""
    p2_ai = ScriptedWayAI({"Sheepdog": ["Way of the Ox"]})
    state = _game(["Sheepdog"], ["Way of the Ox"], [ChooseFirstActionAI(), p2_ai])
    p1, p2 = state.players
    assert state.current_player is p1
    p1.actions = 0
    p1.coins = 5
    p1.buys = 2
    p2.actions = 1
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Copper") for _ in range(3)]

    state.gain_card(p2, get_card("Silver"))

    assert p2_ai.offers == ["Sheepdog"]
    assert p2.actions == 3  # Ox's +2 Actions landed on the reactor
    p2_hand_before = list(p2.hand)

    state.handle_cleanup_phase()

    assert p2.actions == 1
    assert p2.coins == 0
    assert p2.buys == 1
    assert p2.hand == p2_hand_before  # not p2's cleanup: nothing discarded or drawn
    assert p1.actions == 1
    assert p1.coins == 0
    assert p1.buys == 1


def test_off_turn_frog_gives_the_action_but_leaves_no_marker():
    """Way of the Frog played off-turn (p2's Sheepdog during p1's turn): the
    Sheepdog is really in p2's in_play, but it is not discarded from play
    this turn, and Frog's "this turn" ends with p1's turn. A marker would
    survive to p2's own later cleanup and topdeck the card then, so Frog only
    marks cards the turn player is playing. The +1 Action still applies."""
    p2_ai = ScriptedWayAI({"Sheepdog": ["Way of the Frog"]})
    state = _game(["Sheepdog"], ["Way of the Frog"], [ChooseFirstActionAI(), p2_ai])
    p1, p2 = state.players
    assert state.current_player is p1
    sheepdog = get_card("Sheepdog")
    p2.hand = [sheepdog]
    p2.deck = [get_card("Copper") for _ in range(3)]

    state.gain_card(p2, get_card("Silver"))

    assert p2_ai.offers == ["Sheepdog"]
    assert p2.actions == 1  # Frog's +1 Action went to the reactor
    assert p1.actions == 0
    assert sheepdog in p2.in_play
    assert getattr(sheepdog, "_frog_topdeck", False) is False


def test_citadel_does_not_replay_an_off_turn_reaction_play():
    """Renaissance Citadel: "When you play an Action card during your turn, if
    it's the first time you played an Action card this turn, you may play it
    again." p2 owns Citadel and reacts with Sheepdog during p1's turn; that is
    not p2's turn, so Sheepdog resolves once and Citadel's per-turn flag is
    untouched."""
    from dominion.projects import Citadel

    state = _game(
        ["Sheepdog"],
        [],
        [ChooseFirstActionAI(), ChooseFirstActionAI()],
        projects=[Citadel()],
    )
    p1, p2 = state.players
    assert state.current_player is p1
    p2.projects.append(state.projects[0])
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Copper") for _ in range(5)]

    state.gain_card(p2, get_card("Silver"))

    assert len(p2.hand) == 2  # Sheepdog's +2 Cards, exactly once
    assert len(p2.deck) == 3
    assert p2.citadel_used is False
    assert p1.citadel_used is False
    assert state.current_player is p1


def test_citadel_replay_of_an_indirect_play_is_offered_its_own_way():
    """Citadel's replay is a separate play of the card, so it gets its own
    Way offer and chooses independently of the first play. The first Action
    of the turn is played indirectly (as Ghost, Captain or a Throne Room
    target would be): Village resolves normally, then the Citadel replay
    picks Way of the Otter."""
    from dominion.projects import Citadel

    ai = ScriptedWayAI({"Village": [None, "Way of the Otter"]})
    state = _game(
        ["Village"],
        ["Way of the Otter"],
        [ai, ChooseFirstActionAI()],
        projects=[Citadel()],
    )
    p1 = state.players[0]
    assert state.turn_player is p1
    p1.projects.append(state.projects[0])
    village = get_card("Village")
    p1.in_play = [village]
    p1.deck = [get_card("Copper") for _ in range(10)]

    state.play_action_indirectly(p1, village)

    assert ai.offers == ["Village", "Village"]
    assert p1.citadel_used
    assert p1.actions == 2  # Village's +2 Actions; Otter adds none
    assert len(p1.hand) == 3  # Village's +1 Card, then Otter's +2 Cards


def test_procession_does_not_trash_a_card_a_way_moved():
    """Procession: "play it twice. Trash it. Gain an Action card costing
    exactly $1 more than it." If a Way moved the card during either play
    (Turtle sets it aside here), it is no longer anywhere Procession can trash
    it from, so the same instance must not also land in the trash. The gain
    still happens: it keys off the card's cost, not on the trash."""
    ai = ScriptedWayAI({"Village": ["Way of the Turtle", None]})
    state = _game(
        ["Procession", "Village", "Smithy"],
        ["Way of the Turtle"],
        [ai, ChooseFirstActionAI()],
    )
    p1 = state.players[0]
    village = get_card("Village")
    p1.hand = [get_card("Procession"), village]
    p1.deck = [get_card("Copper") for _ in range(5)]
    p1.actions = 1
    state.phase = "action"
    state.supply["Procession"] = 0  # leave Smithy as the only $4 Action
    smithies_before = state.supply["Smithy"]

    state.handle_action_phase()

    assert ai.offers == ["Procession", "Village", "Village"]
    assert p1.turtle_set_aside.count(village) == 1
    assert village not in state.trash
    assert village not in p1.in_play
    assert state.supply["Smithy"] == smithies_before - 1
    assert any(card.name == "Smithy" for card in p1.discard)


def _start_phase_game(ai, way_names):
    state = _game(["Village", "Smithy"], way_names, [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    assert state.turn_player is p1
    p1.deck = [get_card("Copper") for _ in range(20)]
    return state, p1


def _run_start_phase(state):
    state.current_player_index = 0
    state.phase = "start"
    state.handle_start_phase()


def test_ghost_replay_choosing_squirrel_defers_the_draw_to_next_turn():
    """Ghost replays its card during the start phase, before the banked
    Squirrel draw is consumed. A Squirrel chosen there is scheduled for the
    FOLLOWING turn, not drawn later in this same start phase."""
    ai = ScriptedWayAI({"Village": ["Way of the Squirrel"]})
    state, p1 = _start_phase_game(ai, ["Way of the Squirrel"])
    village = get_card("Village")
    p1.ghost_pending_actions = [(village, 1)]

    _run_start_phase(state)

    assert ai.offers == ["Village"]
    assert len(p1.hand) == 0  # not drawn this start phase
    assert p1.squirrel_pending == 2
    assert p1.ghost_pending_actions == []

    _run_start_phase(state)

    assert len(p1.hand) == 2
    assert p1.squirrel_pending == 0


def test_ghost_replay_choosing_turtle_waits_for_next_turn():
    """A Turtle chosen during a Ghost replay sets the card aside for the
    FOLLOWING turn; it must not be picked up and played again later in this
    same start phase."""
    ai = ScriptedWayAI({"Village": ["Way of the Turtle"]})
    state, p1 = _start_phase_game(ai, ["Way of the Turtle"])
    village = get_card("Village")
    p1.ghost_pending_actions = [(village, 1)]

    _run_start_phase(state)

    assert p1.turtle_set_aside == [village]
    assert village not in p1.in_play
    assert p1.actions_this_turn == 1  # the Ghost replay only
    assert p1.actions == 0  # Turtle replaced Village's text; no second play

    _run_start_phase(state)

    assert village in p1.in_play
    assert p1.turtle_set_aside == []
    assert p1.actions == 2  # Village's +2 Actions from the Turtle play


def test_banked_squirrel_and_turtle_from_last_turn_still_fire():
    ai = ScriptedWayAI()
    state, p1 = _start_phase_game(ai, ["Way of the Squirrel", "Way of the Turtle"])
    smithy = get_card("Smithy")
    p1.squirrel_pending = 2
    p1.turtle_set_aside = [smithy]

    _run_start_phase(state)

    assert len(p1.hand) == 5  # Squirrel's 2 + Smithy's 3
    assert smithy in p1.in_play
    assert p1.squirrel_pending == 0
    assert p1.turtle_set_aside == []


def test_turtle_played_card_is_offered_its_own_way():
    """A Turtle-played card is a real play, so it goes through the shared
    helper and gets its own Way offer; choosing Turtle again stashes it for
    the following turn rather than replaying it now."""
    ai = ScriptedWayAI({"Smithy": ["Way of the Turtle"]})
    state, p1 = _start_phase_game(ai, ["Way of the Turtle"])
    smithy = get_card("Smithy")
    p1.turtle_set_aside = [smithy]

    _run_start_phase(state)

    assert ai.offers == ["Smithy"]
    assert p1.actions_this_turn == 1
    assert len(p1.hand) == 0  # Turtle replaced Smithy's draw
    assert p1.turtle_set_aside == [smithy]
    assert smithy not in p1.in_play


def test_frog_marker_expires_when_a_later_replay_moves_the_card():
    """Throne Room on Village: the first play picks Frog (marking the card
    for topdecking at this turn's cleanup), the second picks Turtle, which
    sets the card aside before cleanup can consume the marker. The marker is
    scoped to the turn it was set in, so this turn's cleanup leaves the card
    set aside, and when Turtle plays it next turn that turn's cleanup
    discards it normally instead of honouring the expired Frog."""
    ai = ScriptedWayAI({"Village": ["Way of the Frog", "Way of the Turtle"]})
    state = _game(
        ["Throne Room", "Village"],
        ["Way of the Frog", "Way of the Turtle"],
        [ai, ChooseFirstActionAI()],
    )
    p1 = state.players[0]
    village = get_card("Village")
    p1.hand = [get_card("Throne Room"), village]
    p1.deck = [get_card("Copper") for _ in range(20)]
    p1.actions = 1
    state.phase = "action"

    state.handle_action_phase()

    assert ai.offers == ["Throne Room", "Village", "Village"]
    assert p1.turtle_set_aside == [village]
    assert village not in p1.in_play

    state.handle_cleanup_phase()

    # Still set aside for next turn; not topdecked into the new hand.
    assert p1.turtle_set_aside == [village]
    assert village not in p1.deck
    assert village not in p1.hand

    # Next turn: Turtle plays it (the script is exhausted, so no Way).
    _run_start_phase(state)
    assert village in p1.in_play
    assert p1.turtle_set_aside == []

    state.handle_cleanup_phase()

    # The expired Frog marker did not topdeck it; it was discarded normally.
    assert village in p1.discard
    assert village not in p1.deck
    assert village not in p1.hand


def test_frog_still_topdecks_at_the_cleanup_of_the_turn_it_was_played():
    """Regression guard for the turn-scoped marker: a plain Frog play on a
    turn that went through a real start phase is still topdecked at that
    turn's cleanup and drawn into the next hand."""
    ai = ScriptedWayAI({"Village": ["Way of the Frog"]})
    state, p1 = _start_phase_game(ai, ["Way of the Frog"])
    _run_start_phase(state)
    village = get_card("Village")
    p1.hand = [village]
    p1.actions = 1
    state.phase = "action"

    state.handle_action_phase()
    state.handle_cleanup_phase()

    assert village in p1.hand
    assert village not in p1.discard


def test_vassal_butterfly_returns_a_knight_to_the_knights_pile():
    """Knights share a "Knights" pile; ``card.name`` ("Dame Anna") is not a
    supply key. Butterfly chosen for a Knight that Vassal plays must return it
    to the owning pile (count and pile_order) rather than manufacture a
    synthetic "Dame Anna" pile, then gain a card costing $1 more."""
    ai = ScriptedWayAI({"Dame Anna": ["Way of the Butterfly"]})
    state = _game(["Vassal", "Knights"], ["Way of the Butterfly"], [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    dame_anna = get_card("Dame Anna")
    p1.hand = [get_card("Vassal")]
    p1.deck = [get_card("Copper"), dame_anna]  # top of deck is last
    p1.actions = 1
    state.phase = "action"
    knights_before = state.supply["Knights"]
    assert "Dame Anna" not in state.supply

    state.handle_action_phase()

    assert ai.offers == ["Vassal", "Dame Anna"]
    assert dame_anna not in p1.in_play
    assert state.supply["Knights"] == knights_before + 1
    assert "Dame Anna" not in state.supply
    assert state.pile_order["Knights"][-1] == "Dame Anna"
    # The return happened, so the $6 gain did too.
    assert any(card.cost.coins == dame_anna.cost.coins + 1 for card in p1.discard)


def test_cleanup_resets_off_turn_action_counts_for_every_player():
    """An off-turn Reaction play (p3's Sheepdog during p1's turn) bumps the
    reactor's ``actions_this_turn``. In a 3+ player game that count would
    otherwise survive into p2's turn, so cleanup resets it for everyone."""
    state = _game(
        ["Sheepdog"],
        [],
        [ChooseFirstActionAI(), ChooseFirstActionAI(), ChooseFirstActionAI()],
    )
    p1, p2, p3 = state.players
    assert state.current_player is p1
    p3.hand = [get_card("Sheepdog")]
    p3.deck = [get_card("Copper") for _ in range(3)]

    state.gain_card(p3, get_card("Silver"))

    assert p3.actions_this_turn == 1

    state.handle_cleanup_phase()

    assert p3.actions_this_turn == 0


def _vassal_plays_village(ai, way_names):
    """Vassal (in hand) reveals Village from the top of the deck and plays it."""
    state = _game(["Vassal", "Village"], way_names, [ai, ChooseFirstActionAI()])
    p1 = state.players[0]
    p1.hand = [get_card("Vassal")]
    p1.deck = [get_card("Copper"), get_card("Village")]  # top of deck is last
    p1.actions = 1
    state.phase = "action"
    return state, p1


def test_way_played_indirect_action_still_gets_its_pile_token_bonus():
    """Lost Arts token on Village. Vassal plays Village via Way of the Ox:
    Ox's +2 Actions plus the token's +1, since the Village was still played
    (compare the plain Ox play above, which ends on 2)."""
    ai = ScriptedWayAI({"Village": ["Way of the Ox"]})
    state, p1 = _vassal_plays_village(ai, ["Way of the Ox"])
    state.add_pile_token(p1, "Village", "+1 Action")

    state.handle_action_phase()

    assert ai.offers == ["Vassal", "Village"]
    assert p1.actions == 3
    assert p1.hand == []  # Ox replaced Village's +1 Card


def test_way_played_indirect_action_still_gets_champions_action():
    """Champion in play: +1 Action per Action play. Vassal from hand pays 1
    and earns 1 back from Champion (net 1); Village via Ox is +2 from Ox and
    +1 from Champion, for 4."""
    ai = ScriptedWayAI({"Village": ["Way of the Ox"]})
    state, p1 = _vassal_plays_village(ai, ["Way of the Ox"])
    p1.champions_in_play = 1

    state.handle_action_phase()

    assert ai.offers == ["Vassal", "Village"]
    assert p1.actions == 4


def test_plain_indirect_play_applies_the_pile_token_exactly_once():
    """Regression guard for the on_play refactor: with no Way in the kingdom
    the indirect Village play is +2 Actions from its text plus +1 from the
    token, applied once."""
    ai = ScriptedWayAI()
    state, p1 = _vassal_plays_village(ai, [])
    state.add_pile_token(p1, "Village", "+1 Action")

    state.handle_action_phase()

    assert ai.offers == []
    assert p1.actions == 3
    assert len(p1.hand) == 1  # Village's own +1 Card still drew the Copper
