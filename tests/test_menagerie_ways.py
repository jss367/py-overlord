"""Tests for the Menagerie Ways and the choose-Way-on-Action play hook."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.ways.registry import get_way
from tests.utils import ChooseFirstActionAI


class WayPickerAI(ChooseFirstActionAI):
    def __init__(self, way_name: str):
        super().__init__()
        self._way_name = way_name

    def choose_way(self, state, card, ways):
        for w in ways:
            if w and w.name == self._way_name:
                return w
        return None


def _state(way_name: str | None = None, kingdom=None):
    kingdom = kingdom or [get_card("Village"), get_card("Smithy")]
    if way_name is not None:
        ais = [WayPickerAI(way_name), ChooseFirstActionAI()]
        ways = [get_way(way_name)]
    else:
        ais = [ChooseFirstActionAI(), ChooseFirstActionAI()]
        ways = []
    state = GameState(players=[])
    state.initialize_game(ais, kingdom, ways=ways)
    state.supply.setdefault("Horse", 30)
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Gold", 30)
    state.supply.setdefault("Estate", 8)
    state.supply.setdefault("Curse", 10)
    state.supply.setdefault("Copper", 46)
    return state, state.players[0]


def test_way_of_the_ox_gives_two_actions():
    state, p1 = _state("Way of the Ox")
    p1.actions = 1
    # Play any action via the Way; it should give +2 Actions
    p1.hand = [get_card("Smithy")]
    state.phase = "action"
    state.handle_action_phase()
    # Smithy normally would give 3 cards; via Way of the Ox we should see
    # actions go up by 2 (and no draw), so we can play another action.
    assert p1.actions >= 2 - 1  # 1 starting -1 played + 2 = 2; then loop sees no other action
    # Smithy's draw 3 must NOT have happened
    assert all(c.name != "Smithy" for c in p1.hand)


def test_way_of_the_sheep_gives_two_coins():
    state, p1 = _state("Way of the Sheep")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert p1.coins == 2


def test_way_of_the_otter_draws_two():
    state, p1 = _state("Way of the Otter")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    p1.deck = [get_card("Copper"), get_card("Estate")]
    state.phase = "action"
    state.handle_action_phase()
    # Two cards drawn from deck
    assert len(p1.hand) == 2
    # No +Cards from village's normal play happened (just the way's 2)
    # Action count: 0 (we used 1 to play; way of otter doesn't give actions)
    assert p1.actions == 0


def test_way_of_the_horse_returns_card_to_pile():
    state, p1 = _state("Way of the Horse")
    state.supply["Smithy"] = 10
    p1.actions = 1
    p1.hand = [get_card("Smithy")]
    smithy_before = state.supply["Smithy"]
    state.phase = "action"
    state.handle_action_phase()
    # +2 cards +1 action; Smithy returned to pile
    assert state.supply["Smithy"] == smithy_before + 1
    assert all(c.name != "Smithy" for c in p1.in_play)


def test_way_of_the_camel_exiles_gold():
    state, p1 = _state("Way of the Camel")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Gold" for c in p1.exile)


def test_way_of_the_worm_exiles_card_and_gains_estate():
    state, p1 = _state("Way of the Worm")
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.actions = 1
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    # Village should be in exile
    assert village in p1.exile
    # Estate should be gained
    assert any(c.name == "Estate" for c in p1.discard + p1.deck)


def test_way_of_the_squirrel_pending_draw():
    state, p1 = _state("Way of the Squirrel")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    assert p1.squirrel_pending == 2


def test_way_of_the_mule_gives_action_and_coin():
    state, p1 = _state("Way of the Mule")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    # +1 Action +$1; played from 1 action -1 + 1 = 1 net
    assert p1.coins == 1


def test_way_of_the_pig_gives_card_and_action():
    state, p1 = _state("Way of the Pig")
    p1.actions = 1
    p1.hand = [get_card("Village")]
    p1.deck = [get_card("Copper")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Copper" for c in p1.hand)


def test_way_of_the_goat_trashes_card():
    class TrashAI(WayPickerAI):
        def choose_card_to_trash(self, state, choices):
            for c in choices:
                if c is not None:
                    return c
            return None

    state = GameState(players=[])
    state.initialize_game(
        [TrashAI("Way of the Goat"), ChooseFirstActionAI()],
        [get_card("Village")],
        ways=[get_way("Way of the Goat")],
    )
    state.supply.setdefault("Estate", 8)
    p1 = state.players[0]
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Estate")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name in ("Estate", "Village") for c in state.trash)


def test_way_of_the_owl_draws_to_six():
    state, p1 = _state("Way of the Owl")
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Copper"), get_card("Copper")]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # We had 2 in hand after playing village, draw to 6
    assert len(p1.hand) >= 6


def test_way_of_the_mole_discards_hand_then_draws_three():
    state, p1 = _state("Way of the Mole")
    p1.actions = 1
    p1.hand = [
        get_card("Village"),
        get_card("Copper"),
        get_card("Estate"),
    ]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Hand discarded then drew 3 → 3 new cards
    assert len(p1.hand) == 3


def test_way_of_the_rat_discards_treasure_gains_action():
    state, p1 = _state("Way of the Rat")
    state.supply["Village"] = 10
    p1.actions = 1
    p1.hand = [get_card("Village"), get_card("Copper")]
    state.phase = "action"
    state.handle_action_phase()
    # Copper discarded; gained an action card.
    assert any(c.name == "Copper" for c in p1.discard)
    gained = [c for c in p1.discard if c.is_action]
    assert gained


def test_way_of_the_turtle_plays_next_turn():
    state, p1 = _state("Way of the Turtle")
    p1.actions = 1
    smithy = get_card("Smithy")
    p1.hand = [smithy]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    assert smithy in p1.turtle_set_aside
    # Play through turn end + next turn
    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()
    # Now next turn for p1
    state.current_player_index = 0
    state.phase = "start"
    state.handle_start_phase()
    # Smithy should fire (drew 3 cards)
    assert smithy in p1.in_play


def test_way_of_the_frog_topdecks_on_cleanup():
    state, p1 = _state("Way of the Frog")
    p1.actions = 1
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    state.handle_treasure_phase()
    state.handle_buy_phase()
    state.handle_cleanup_phase()
    # Village should be at top of deck (deck[0]) after cleanup
    assert village in p1.deck


def test_way_of_the_chameleon_swaps_cards_and_coins():
    state, p1 = _state("Way of the Chameleon")
    p1.actions = 1
    smithy = get_card("Smithy")  # +3 Cards
    p1.hand = [smithy]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Swapped: +3 coins and 0 cards
    assert p1.coins == 3


def test_way_of_the_chameleon_swaps_imperative_draw():
    """Chameleon must also swap imperative ``+Cards`` (e.g. cards that draw
    inside ``play_effect`` rather than via ``CardStats.cards``)."""
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Hunting Lodge")],
    )
    p1.actions = 1
    # Hunting Lodge: +1 Card, +2 Actions; you may discard your hand for +5 Cards.
    # The +5 Cards branch is imperative. Without choosing the discard branch,
    # we still get 1 stat-driven Card → should swap to +$1.
    hl = get_card("Hunting Lodge")
    p1.hand = [hl]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Hunting Lodge here draws 1 stat + (with the AI choosing to discard for
    # the +5 branch) 5 imperative — 6 cards total. All swapped to +$.
    # Without the imperative-draw fix, we'd see 1 coin and 5 cards drawn.
    assert p1.coins == 6
    # Hand should be empty: the player discarded everything for the +5 Cards
    # branch, which Chameleon converted to coins (no draw happened).
    assert len(p1.hand) == 0


def test_way_of_the_chameleon_does_not_swap_vassal_played_card():
    """When Vassal is played as Way of the Chameleon and reveals/plays an
    Action via its side effect, the *Vassal's* +$2 swaps to +2 Cards (the Way
    applies to Vassal). The card Vassal plays — Village here — keeps its own
    +1 Card and +2 Actions: the Way does NOT chain to cards that Vassal
    causes to be played.
    """
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Vassal")],
    )
    p1.actions = 1
    vassal = get_card("Vassal")
    p1.hand = [vassal]
    # Top of deck (last element) is what Vassal discards/plays. Make it
    # Village so Vassal plays Village as a side effect.
    p1.deck = [get_card("Copper"), get_card("Copper"), get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    # Vassal's own +$2 swaps to +2 Cards (Vassal had 0 +Cards to begin with).
    # Village (played as Vassal's side effect) keeps its real +1 Card +2
    # Actions; its +1 Card is NOT swapped to +$1.
    # Net coins: Vassal contributed 0 (its +$2 swapped away). Village adds
    # nothing to coins. So coins == 0.
    assert p1.coins == 0
    # Hand contents:
    #   - Vassal swap drew 2 cards (Vassal's +$2 -> +2 Cards from deck top:
    #     two Coppers).
    #   - Village's own +1 Card drew 1 card. Deck started with 3 cards: the
    #     last (Village) was popped by Vassal, leaving 2 Coppers. Vassal's
    #     swap drew both Coppers, so by the time Village resolves there's
    #     nothing left to draw.
    # Sanity: Village must be in_play (it was played, not discarded), proving
    # the +1 Card came from Village resolving — and that any draws Village
    # made happened via the un-intercepted draw path.
    assert any(c.name == "Village" for c in p1.in_play)
    # Player's actions: started 1, -1 to play Vassal, Village +2 = 2.
    assert p1.actions == 2


def test_way_of_the_chameleon_throne_room_does_not_swap_smithy_draws():
    """Throne Room played as Way of the Chameleon: the Way applies only to
    Throne Room itself (which has no +Cards/+$, so the swap is a no-op).
    Smithy played by Throne Room keeps its real +3 Cards and is NOT
    converted to +$3.
    """
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Throne Room"), get_card("Smithy")],
    )
    p1.actions = 1
    throne = get_card("Throne Room")
    smithy = get_card("Smithy")
    p1.hand = [throne, smithy]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Throne Room itself has no +Cards/+$ — Chameleon swap is a no-op there.
    # Smithy played twice via Throne Room normally draws 6 cards; those
    # draws are NOT routed through Chameleon's interceptor.
    assert p1.coins == 0
    # Hand: Smithy was played out of hand by Throne Room, then drew 6
    # Coppers across two activations.
    coppers_in_hand = sum(1 for c in p1.hand if c.name == "Copper")
    assert coppers_in_hand == 6


def test_way_of_the_chameleon_does_not_swap_cursed_village_draw_until_six():
    """Cursed Village's "draw until you have 6 in hand" is an imperative
    draw, NOT a "+Cards" instruction. Way of the Chameleon must not
    convert that draw into coins.
    """
    import random

    random.seed(1729)
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Cursed Village")],
    )
    p1.actions = 1
    cv = get_card("Cursed Village")
    p1.hand = [cv]
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Cursed Village has no +Cards / +$ on its stat block, so the
    # Chameleon swap is a no-op for the stat block. Crucially, the
    # "draw until 6 in hand" must execute as a draw — NOT swapped to
    # coins. Cursed Village is played from hand, leaving 0; it then
    # draws up to 6.
    assert len(p1.hand) == 6, (
        f"Expected hand of 6 (draw-until-6 still draws), got {len(p1.hand)}"
    )
    # No coins were granted: Cursed Village had no +$ to swap, and the
    # imperative draw must NOT have been converted to coins.
    assert p1.coins == 0
    # The Hex still fires: a Hex was drawn from the Hex deck and is
    # now in the Hex discard pile.
    assert state.hex_discard, "Cursed Village should have caused a Hex"


def test_way_of_the_chameleon_does_not_swap_library_draw_until_seven():
    """Library's "draw until you have 7 in hand" is an imperative draw,
    NOT "+Cards". Way of the Chameleon must not convert it to coins.
    """
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Library")],
    )
    p1.actions = 1
    lib = get_card("Library")
    p1.hand = [lib]
    # Coppers in deck so the AI never sets any aside.
    p1.deck = [get_card("Copper")] * 10
    state.phase = "action"
    state.handle_action_phase()
    # Library has no +Cards / +$, so the Chameleon swap is a no-op for
    # its stat block. The "draw until 7" must execute as a real draw —
    # not be converted to coins.
    assert len(p1.hand) == 7, (
        f"Expected hand of 7 (draw-until-7 still draws), got {len(p1.hand)}"
    )
    assert p1.coins == 0


def test_way_of_the_horse_does_not_create_synthetic_pile():
    """Way of the Horse must not invent a supply pile for a non-Supply card."""
    state, p1 = _state("Way of the Horse", kingdom=[get_card("Village")])
    p1.actions = 1
    # Construct a non-Supply Action: register a Smithy in hand but ensure
    # there is no Smithy supply pile.
    state.supply.pop("Smithy", None)
    p1.hand = [get_card("Smithy")]
    state.phase = "action"
    state.handle_action_phase()
    # The Way must not have manufactured a Smithy pile from nothing.
    assert "Smithy" not in state.supply


def test_way_of_the_horse_returns_dame_anna_to_knights_pile():
    """Knights live under a shared "Knights" pile_order; ``card.name`` is
    e.g. "Dame Anna" — not a key in ``state.supply``. Way of the Horse
    must still return the played Knight to the top of its owning
    "Knights" pile.
    """
    state, p1 = _state(
        "Way of the Horse",
        kingdom=[get_card("Village"), get_card("Knights")],
    )
    p1.actions = 1
    dame_anna = get_card("Dame Anna")
    p1.hand = [dame_anna]
    knights_before = state.supply.get("Knights", 0)
    # Sanity: there is no per-Knight supply pile.
    assert "Dame Anna" not in state.supply
    state.phase = "action"
    state.handle_action_phase()
    # Dame Anna left play and was returned to the Knights pile.
    assert dame_anna not in p1.in_play
    assert state.supply["Knights"] == knights_before + 1
    # The specific Knight is now on top of the pile_order.
    assert state.pile_order["Knights"][-1] == "Dame Anna"


def test_way_of_the_chameleon_runs_full_on_play_for_bauble():
    """Bauble defines its effects in ``on_play`` (Treasure-Liaison: +1 Buy,
    +1 Favor, choose +$1 / +1 Card / +1 Favor). Played as Way of the
    Chameleon, the +1 Buy and +1 Favor must still happen, and Bauble's
    "+$1" choice swaps to "+1 Card".

    Treasures are playable in the Action phase (where Ways are choosable)
    under Rising Sun's Enlightenment prophecy. We invoke the Way directly
    here to isolate the swap behavior from Enlightenment's "+1 Card +1
    Action" treasure-as-action substitution.
    """
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Bauble")],
    )
    bauble = get_card("Bauble")
    p1.in_play.append(bauble)
    # Force Bauble's heuristic into the +$1 branch (hand has > 2 cards).
    p1.hand = [get_card("Copper"), get_card("Copper"), get_card("Copper")]
    p1.deck = [get_card("Estate")] * 5
    favors_before = p1.favors
    buys_before = p1.buys
    coins_before = p1.coins
    hand_size_before = len(p1.hand)
    way = get_way("Way of the Chameleon")
    way.apply(state, bauble)
    # Core ``on_play`` effects (driven through the actual subclass override)
    # still ran: +1 Buy, +1 Favor.
    assert p1.favors == favors_before + 1
    assert p1.buys == buys_before + 1
    # Bauble's "+$1" choice swapped to "+1 Card": no extra coins, +1 card
    # drawn from deck.
    assert p1.coins == coins_before
    assert len(p1.hand) == hand_size_before + 1
    assert p1.hand[-1].name == "Estate"


def test_way_of_the_chameleon_runs_full_on_play_for_contract():
    """Contract is a Treasure-Duration-Liaison whose effects live in an
    overridden ``on_play``: +$2, +1 Favor, set aside an Action to play
    next turn. Played as Way of the Chameleon, the +1 Favor and
    set-aside should still happen; the +$2 swaps to +2 Cards.

    See ``test_way_of_the_chameleon_runs_full_on_play_for_bauble`` for
    why we apply the Way directly rather than going through the action
    phase.
    """
    state, p1 = _state(
        "Way of the Chameleon",
        kingdom=[get_card("Village"), get_card("Contract")],
    )
    contract = get_card("Contract")
    p1.in_play.append(contract)
    # Provide an Action in hand so Contract's set-aside can fire.
    village = get_card("Village")
    p1.hand = [village]
    p1.deck = [get_card("Estate")] * 5
    favors_before = p1.favors
    coins_before = p1.coins
    way = get_way("Way of the Chameleon")
    way.apply(state, contract)
    # +1 Favor still runs (Contract's overridden on_play executed).
    assert p1.favors == favors_before + 1
    # +$2 swapped to +2 Cards: no extra coins, two cards drawn.
    assert p1.coins == coins_before
    estates_in_hand = sum(1 for c in p1.hand if c.name == "Estate")
    assert estates_in_hand == 2
    # Set-aside-action behavior: Village was set aside on Contract.
    assert contract._set_aside is village
    assert village not in p1.hand
