"""Tests for the Adventures Events."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI, TrashFirstAI


def _new_state(kingdom_card_names=None):
    if kingdom_card_names is None:
        kingdom_card_names = ["Village", "Smithy"]
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card(n) for n in kingdom_card_names])
    return state


def test_alms_gains_card_when_no_treasure_in_play():
    state = _new_state()
    player = state.players[0]
    player.hand = [get_card("Estate")]
    player.in_play = []
    state.phase = "buy"
    Alms = get_event("Alms")
    assert Alms.may_be_bought(state, player)
    Alms.on_buy(state, player)
    # Gained at least one card costing up to $4.
    assert any(c.cost.coins <= 4 for c in player.discard)
    # Alms is once per turn.
    assert not Alms.may_be_bought(state, player)


def test_alms_blocked_by_treasure_in_play():
    state = _new_state()
    player = state.players[0]
    player.in_play = [get_card("Copper")]
    Alms = get_event("Alms")
    assert not Alms.may_be_bought(state, player)


def test_borrow_gives_buy_coin_and_minus_card():
    state = _new_state()
    player = state.players[0]
    Borrow = get_event("Borrow")
    Borrow.on_buy(state, player)
    assert player.buys == 2
    assert player.coins == 1
    assert player.minus_card_tokens == 1
    assert not Borrow.may_be_bought(state, player)


def test_quest_discards_cards_for_gold():
    state = _new_state()
    player = state.players[0]
    player.hand = [get_card("Estate") for _ in range(6)]
    Quest = get_event("Quest")
    Quest.on_buy(state, player)
    assert any(c.name == "Gold" for c in player.discard)


def test_save_sets_aside_card_returns_next_turn():
    state = _new_state()
    player = state.players[0]
    test_card = get_card("Copper")
    player.hand = [test_card]
    Save = get_event("Save")
    Save.on_buy(state, player)
    assert test_card in player.save_set_aside
    assert test_card not in player.hand
    assert player.buys == 2


def test_scouting_party_keeps_2_discards_3():
    state = _new_state()
    player = state.players[0]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []
    ScoutingParty = get_event("Scouting Party")
    ScoutingParty.on_buy(state, player)
    assert len(player.deck) == 2
    assert len(player.discard) == 3
    assert player.buys == 2


def test_travelling_fair_gives_2_buys_and_topdeck_active():
    state = _new_state()
    player = state.players[0]
    TravellingFair = get_event("Travelling Fair")
    TravellingFair.on_buy(state, player)
    assert player.buys == 3
    assert player.travelling_fair_active is True


def test_bonfire_trashes_in_play():
    ai = TrashFirstAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]
    c1 = get_card("Copper")
    c2 = get_card("Estate")
    player.in_play = [c1, c2]
    Bonfire = get_event("Bonfire")
    Bonfire.on_buy(state, player)
    assert c1 in state.trash or c2 in state.trash


def test_expedition_extra_draws_at_end_of_turn():
    state = _new_state()
    player = state.players[0]
    Expedition = get_event("Expedition")
    Expedition.on_buy(state, player)
    assert player.expedition_extra_draws == 2


def test_ferry_places_minus2_cost_token():
    state = _new_state(["Smithy"])
    player = state.players[0]
    Ferry = get_event("Ferry")
    Ferry.on_buy(state, player)
    pile = state.player_token_pile(player, "-$2 cost")
    assert pile == "Smithy"
    # Cost reduced from $4 to $2.
    smithy = get_card("Smithy")
    assert state.get_card_cost(player, smithy) == 2


def test_plan_places_trash_token():
    state = _new_state(["Smithy"])
    player = state.players[0]
    Plan = get_event("Plan")
    Plan.on_buy(state, player)
    assert state.player_token_pile(player, "trash") == "Smithy"


def test_mission_grants_extra_no_buy_turn():
    state = _new_state()
    player = state.players[0]
    Mission = get_event("Mission")
    Mission.on_buy(state, player)
    assert player.mission_used_this_turn
    # Mission's "no buys" restriction must NOT apply to the current turn —
    # it only applies on the granted extra turn. So the flag is deferred.
    assert not player.mission_no_buy_turn
    assert player.mission_extra_turn_pending
    assert state.extra_turn


def test_mission_does_not_block_remaining_buys_on_buy_turn():
    """Buying Mission with remaining Buys must NOT shut off further buys
    on the current turn. The "no buys" restriction is only for the extra
    turn that Mission grants."""
    state = _new_state()
    player = state.players[0]
    player.buys = 2
    player.coins = 4
    Mission = get_event("Mission")
    Mission.on_buy(state, player)
    # Player should still be able to buy from the supply this turn.
    affordable = state._get_affordable_cards(player)
    assert affordable, "Player must still be able to buy after Mission on the same turn"


def test_mission_no_buys_on_granted_extra_turn():
    """On the extra turn granted by Mission, buys are not allowed."""
    state = _new_state()
    player = state.players[0]
    Mission = get_event("Mission")
    Mission.on_buy(state, player)
    # Simulate cleanup ending the buy turn and entering the extra turn.
    state.handle_cleanup_phase()
    # The extra turn now begins. Re-enter start phase.
    state.phase = "start"
    state.handle_start_phase()
    # On the extra (Mission) turn, the no-buy flag is now set.
    assert player.mission_no_buy_turn
    affordable = state._get_affordable_cards(player)
    assert affordable == [], "On Mission's extra turn, no cards may be bought"


def test_pilgrimage_gains_action_copies():
    state = _new_state(["Village", "Smithy"])
    player = state.players[0]
    player.in_play = [get_card("Village"), get_card("Smithy")]
    # Pilgrimage flips the token; gains only if it's now face-up. Start face-down
    # so the flip turns it face-up.
    player.journey_token_face_up = False
    Pilgrimage = get_event("Pilgrimage")
    Pilgrimage.on_buy(state, player)
    assert player.journey_token_face_up  # flipped face-up
    names = [c.name for c in player.discard]
    assert "Village" in names
    assert "Smithy" in names


def test_ball_costs_one_and_gains_two():
    state = _new_state()
    player = state.players[0]
    player.coins = 5
    Ball = get_event("Ball")
    Ball.on_buy(state, player)
    assert player.coins == 4  # -$1 token
    assert len(player.discard) == 2


def test_raid_minus_card_tokens_and_silvers():
    state = _new_state()
    state2 = GameState(players=[])
    ai1 = ChooseFirstActionAI()
    ai2 = ChooseFirstActionAI()
    state2.initialize_game([ai1, ai2], [get_card("Smithy")])
    p1, p2 = state2.players
    p1.in_play = [get_card("Silver"), get_card("Silver")]
    Raid = get_event("Raid")
    Raid.on_buy(state2, p1)
    assert p2.minus_card_tokens == 1
    silver_count = sum(1 for c in p1.discard if c.name == "Silver")
    assert silver_count == 2


def test_seaway_places_buy_token():
    state = _new_state(["Village"])
    player = state.players[0]
    Seaway = get_event("Seaway")
    Seaway.on_buy(state, player)
    assert state.player_token_pile(player, "+1 Buy") == "Village"


def test_trade_trashes_for_silvers():
    ai = TrashFirstAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]
    player.hand = [get_card("Estate"), get_card("Estate")]
    Trade = get_event("Trade")
    Trade.on_buy(state, player)
    silvers_gained = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers_gained == 2


def test_lost_arts_places_action_token():
    state = _new_state(["Smithy"])
    player = state.players[0]
    LostArts = get_event("Lost Arts")
    LostArts.on_buy(state, player)
    assert state.player_token_pile(player, "+1 Action") == "Smithy"


def test_pathfinding_places_card_token():
    state = _new_state(["Smithy"])
    player = state.players[0]
    Pathfinding = get_event("Pathfinding")
    Pathfinding.on_buy(state, player)
    assert state.player_token_pile(player, "+1 Card") == "Smithy"


def test_inheritance_estate_plays_as_inherited_action():
    state = _new_state(["Village"])
    player = state.players[0]
    player.inherited_action_name = "Village"
    estate = get_card("Estate")
    player.hand = [estate]
    player.deck = [get_card("Copper") for _ in range(3)]
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Estate played as Village: +1 Card, +2 Actions. Started at 1 action,
    # spent 1 to play, gained 2 = 2 actions.
    assert player.actions == 2


def test_inheritance_estate_as_guide_sets_aside_estate_on_tavern():
    """Inheriting a Reserve card like Guide must set aside the *Estate
    instance itself* on the Tavern mat — NOT a fresh phantom Guide. The
    fresh-Guide bug would leak persistent phantom cards onto the Tavern
    mat that re-fire each turn."""
    state = _new_state(["Guide"])
    player = state.players[0]
    player.inherited_action_name = "Guide"
    estate = get_card("Estate")
    player.hand = [estate]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # The Estate (not a Guide) should be on the Tavern mat now.
    assert estate in player.tavern_mat, (
        "Inherited-as-Guide must place the Estate on the Tavern mat"
    )
    # No phantom Guide on the mat.
    assert not any(c.name == "Guide" for c in player.tavern_mat), (
        "A fresh Guide instance must NOT appear on the Tavern mat"
    )


def test_inheritance_sets_aside_card():
    state = _new_state(["Village"])
    player = state.players[0]
    Inheritance = get_event("Inheritance")
    Inheritance.on_buy(state, player)
    assert player.inherited_action_name == "Village"
    assert player.inheritance_used


def test_pile_token_action_gives_bonus_on_play():
    """When +1 Action token sits on Smithy, playing Smithy gives +1 Action."""
    state = _new_state(["Smithy"])
    player = state.players[0]
    state.add_pile_token(player, "Smithy", "+1 Action")
    smithy = get_card("Smithy")
    player.hand = [smithy]
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Smithy itself doesn't give +1 Action by default; the token does.
    # actions consumed = 1 (Smithy play), gained = 1 (token), so == initial -0.
    # But Smithy's text doesn't give an Action; token gave +1; net = 1 - 1 + 1 = 1.
    assert player.actions == 1


def test_pile_token_card_bonus_draws_extra():
    state = _new_state(["Village"])
    player = state.players[0]
    state.add_pile_token(player, "Village", "+1 Card")
    village = get_card("Village")
    player.hand = [village]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Village normally draws 1; with +1 Card token, draws 2.
    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 2


def test_pile_token_bonus_fires_per_throne_room_replay():
    """Throne Room replays a card; each replay must trigger pile-token
    bonuses. With +1 Card token on Smithy, Throne Room on Smithy draws
    Smithy's 3 cards x 2 plays + 2 token bonuses = 8 cards total."""
    state = _new_state(["Smithy", "Throne Room"])
    player = state.players[0]
    state.add_pile_token(player, "Smithy", "+1 Card")
    throne = get_card("Throne Room")
    smithy = get_card("Smithy")
    player.hand = [throne, smithy]
    # 8 unique-ish coppers in deck so we can count drawn cards precisely.
    player.deck = [get_card("Copper") for _ in range(10)]
    player.discard = []
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Throne Room (no +cards) → Smithy played twice. Smithy = +3 cards.
    # Token = +1 card per Smithy play. So 3+1 + 3+1 = 8.
    coppers_in_hand = sum(1 for c in player.hand if c.name == "Copper")
    assert coppers_in_hand == 8, (
        f"Expected 8 cards drawn (3+1 per Smithy play, twice), got {coppers_in_hand}"
    )
