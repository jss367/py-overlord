"""Tests for the 23 Allies (the chosen-once-per-game cards)."""

from dominion.allies.registry import ALLY_TYPES, get_ally
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import ChooseFirstActionAI, DummyAI


def _state(ally_name: str) -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.allies = [get_ally(ally_name)]
    state.supply = {}
    return state, player


def test_all_allies_registered():
    expected = {
        "Architects' Guild", "Band of Nomads", "Cave Dwellers",
        "Circle of Witches", "City-state", "Coastal Haven",
        "Crafters' Guild", "Desert Guides", "Family of Inventors",
        "Fellowship of Scribes", "Forest Dwellers", "Gang of Pickpockets",
        "Island Folk", "League of Bankers", "League of Shopkeepers",
        "Market Towns", "Mountain Folk", "Order of Astrologers",
        "Order of Masons", "Peaceful Cult", "Plateau Shepherds",
        "Trappers' Lodge", "Woodworkers' Guild",
    }
    assert set(ALLY_TYPES.keys()) == expected
    assert len(ALLY_TYPES) == 23


def test_get_ally_returns_instance():
    for name in ALLY_TYPES:
        ally = get_ally(name)
        assert ally.name == name


def test_random_ally_chosen_when_liaison_in_kingdom():
    """initialize_game picks an Ally when at least one Liaison is in
    the kingdom and none was supplied."""
    from dominion.cards.registry import get_card

    class _AI(DummyAI):
        @property
        def name(self):
            return "p1"

    p1, p2 = _AI(), _AI()
    state = GameState(players=[])
    state.initialize_game([p1, p2], [get_card("Underling"), get_card("Village")])
    assert len(state.allies) == 1


def test_no_ally_when_no_liaison():
    class _AI(DummyAI):
        @property
        def name(self):
            return "p1"

    state = GameState(players=[])
    state.initialize_game(
        [_AI(), _AI()], [get_card("Village"), get_card("Smithy")]
    )
    assert state.allies == []


def test_mountain_folk_spends_5_favors_for_3_cards():
    state, player = _state("Mountain Folk")
    player.favors = 5
    player.deck = [get_card("Copper") for _ in range(3)]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    assert len(player.hand) == 3


def test_mountain_folk_skipped_below_threshold():
    state, player = _state("Mountain Folk")
    player.favors = 4
    player.deck = [get_card("Copper") for _ in range(3)]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 4
    assert len(player.hand) == 0


def test_architects_guild_spends_2_favors_on_victory_gain():
    state, player = _state("Architects' Guild")
    state.supply["Duchy"] = 1
    state.supply["Silver"] = 5
    state.supply["Smithy"] = 5
    player.favors = 3
    duchy = get_card("Duchy")
    state.gain_card(player, duchy)
    # Architects' Guild should spend 2 favors and gain a card cheaper than Duchy ($5).
    assert player.favors == 1
    # Should have gained a card costing $4 (Smithy) or $3 (Silver).
    gained_names = {c.name for c in player.discard}
    assert "Smithy" in gained_names or "Silver" in gained_names


def test_band_of_nomads_spends_favor_on_3plus_gain():
    state, player = _state("Band of Nomads")
    state.supply["Silver"] = 5
    player.favors = 1
    player.actions = 0
    silver = get_card("Silver")
    state.gain_card(player, silver)
    # Player had 0 actions, hand non-empty? Actually hand is empty by default;
    # band picks +1 Action when starved.
    # If hand is empty, +1 Card is preferred.
    assert player.favors == 0


def test_band_of_nomads_skips_low_cost_gain():
    state, player = _state("Band of Nomads")
    state.supply["Copper"] = 5
    player.favors = 1
    copper = get_card("Copper")
    state.gain_card(player, copper)
    assert player.favors == 1


def test_circle_of_witches_curses_opponents():
    p1 = PlayerState(DummyAI())
    p2 = PlayerState(DummyAI())
    state = GameState(players=[p1, p2])
    state.supply = {"Curse": 5}
    state.allies = [get_ally("Circle of Witches")]
    p1.favors = 3
    witch = get_card("Witch")
    p1.in_play.append(witch)
    state.current_player_index = 0
    state.allies[0].on_play_card(state, p1, witch)
    assert p1.favors == 0
    assert any(c.name == "Curse" for c in p2.discard)


def test_market_towns_spends_favors_to_play_actions():
    state, player = _state("Market Towns")
    player.ai = ChooseFirstActionAI()
    player.favors = 2
    village = get_card("Village")
    smithy = get_card("Smithy")
    player.hand = [village, smithy]
    state.current_player_index = 0
    state.allies[0].on_buy_phase_start(state, player)
    # Played both Actions; spent 2 Favors.
    assert player.favors == 0
    assert village in player.in_play or smithy in player.in_play


def test_peaceful_cult_trashes_junk():
    state, player = _state("Peaceful Cult")
    player.favors = 2
    player.hand = [get_card("Curse"), get_card("Estate"), get_card("Gold")]
    state.allies[0].on_buy_phase_start(state, player)
    assert player.favors == 0
    trashed_names = [c.name for c in state.trash]
    assert "Curse" in trashed_names
    assert "Estate" in trashed_names
    assert any(c.name == "Gold" for c in player.hand)


def test_plateau_shepherds_score_bonus():
    state, player = _state("Plateau Shepherds")
    player.favors = 3
    # Three $2 cards (e.g. Estate at $2 cost).
    player.deck = [get_card("Estate") for _ in range(3)]
    bonus = state.allies[0].score_bonus(state, player)
    assert bonus == 4 * 3


def test_island_folk_schedules_extra_turn():
    state, player = _state("Island Folk")
    player.favors = 5
    state.allies[0].on_turn_end(state, player)
    assert player.favors == 0
    assert player.outpost_pending


def test_league_of_bankers_grants_coin_per_4_favors():
    state, player = _state("League of Bankers")
    player.favors = 9
    state.allies[0].on_buy_phase_end(state, player)
    assert player.coin_tokens == 2  # 9 // 4 = 2


def test_trappers_lodge_topdecks_gain():
    state, player = _state("Trappers' Lodge")
    state.supply["Silver"] = 5
    player.favors = 1
    silver = get_card("Silver")
    state.gain_card(player, silver)
    # Silver was costed at $3, should be topdecked.
    assert player.favors == 0
    assert silver in player.deck
    assert silver not in player.discard


def test_woodworkers_guild_trashes_action_and_gains_better():
    state, player = _state("Woodworkers' Guild")
    state.supply["Smithy"] = 5
    state.supply["Village"] = 5
    player.favors = 1
    village = get_card("Village")
    player.hand = [village]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    # Village trashed, an Action up to $5 gained.
    assert village in state.trash
    assert player.discard or any(c.name == "Smithy" for c in player.discard)


def test_crafters_guild_gains_card_to_hand():
    state, player = _state("Crafters' Guild")
    state.supply["Silver"] = 5
    state.supply["Smithy"] = 5
    player.favors = 2
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    assert any(c.name in {"Smithy", "Silver"} for c in player.hand)


def test_desert_guides_redraws_junk_hand():
    state, player = _state("Desert Guides")
    player.favors = 1
    player.hand = [
        get_card("Curse"), get_card("Curse"), get_card("Curse"),
        get_card("Copper"), get_card("Copper"),
    ]
    player.deck = [get_card("Gold") for _ in range(5)]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    assert all(c.name == "Gold" for c in player.hand)


def test_fellowship_of_scribes_draws_when_hand_low():
    state, player = _state("Fellowship of Scribes")
    player.favors = 1
    player.deck = [get_card("Silver")]
    player.hand = [get_card("Copper")]
    underling = get_card("Underling")
    player.in_play.append(underling)
    state.allies[0].on_play_card(state, player, underling)
    assert player.favors == 0
    assert any(c.name == "Silver" for c in player.hand)


def test_gang_of_pickpockets_spends_favor_first():
    state, player = _state("Gang of Pickpockets")
    player.favors = 1
    player.hand = [get_card("Copper")]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    # No discard since the Favor was spent.
    assert any(c.name == "Copper" for c in player.hand)


def test_gang_of_pickpockets_discards_when_no_favors():
    state, player = _state("Gang of Pickpockets")
    player.favors = 0
    player.hand = [get_card("Estate")]
    state.allies[0].on_turn_start(state, player)
    assert any(c.name == "Estate" for c in player.discard)


def test_family_of_inventors_marks_pile_with_minus_1():
    state, player = _state("Family of Inventors")
    state.supply["Silver"] = 5
    state.supply["Smithy"] = 5
    player.favors = 1
    state.allies[0].on_turn_end(state, player)
    assert player.favors == 0
    assert getattr(state, "family_inventor_tokens", {})


def test_order_of_masons_banks_bonus_draws():
    state, player = _state("Order of Masons")
    player.favors = 4
    state.allies[0].on_turn_end(state, player)
    # 4 favors -> 2 pairs -> +2 cards next turn.
    assert player.favors == 0
    assert getattr(player, "order_of_masons_bonus", 0) == 2


def test_league_of_shopkeepers_grants_bonus_favor_on_liaison_play():
    state, player = _state("League of Shopkeepers")
    underling = get_card("Underling")
    player.in_play.append(underling)
    favors_before = player.favors
    state.allies[0].on_play_card(state, player, underling)
    # Ally grants +1 Favor on top of Underling's own Favor (which fires
    # via on_play not via this hook).
    assert player.favors == favors_before + 1


def test_city_state_plays_action_for_two_favors():
    state, player = _state("City-state")
    state.phase = "treasure"
    player.ai = ChooseFirstActionAI()
    player.favors = 2
    village = get_card("Village")
    player.hand = [village]
    silver = get_card("Silver")
    state.allies[0].on_play_card(state, player, silver)
    assert player.favors == 0
    assert village in player.in_play


def test_coastal_haven_keeps_actions_for_next_turn():
    state, player = _state("Coastal Haven")
    player.favors = 2
    village = get_card("Village")
    player.hand = [village, get_card("Copper")]
    state.allies[0].on_turn_end(state, player)
    assert player.favors == 1  # One Action kept; one Favor spent
    assert village in player.foresight_set_aside


def test_forest_dwellers_reorders_top_3():
    state, player = _state("Forest Dwellers")
    player.favors = 1
    player.deck = [
        get_card("Copper"), get_card("Estate"), get_card("Smithy"),
    ]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0


def test_order_of_astrologers_topdecks_from_discard_when_shuffle_imminent():
    state, player = _state("Order of Astrologers")
    player.favors = 1
    player.deck = []
    player.discard = [get_card("Smithy"), get_card("Curse")]
    state.allies[0].on_turn_start(state, player)
    assert player.favors == 0
    assert any(c.name == "Smithy" for c in player.deck)
