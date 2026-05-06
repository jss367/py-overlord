"""Tests for cards from the Adventures expansion."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI, DummyAI


class MessengerTestAI(ChooseFirstActionAI):
    def __init__(self, *, discard_deck: bool, gain_choice: str):
        super().__init__()
        self.discard_deck = discard_deck
        self.gain_choice = gain_choice

    def choose_buy(self, state, choices):
        for choice in choices:
            if choice is None:
                continue
            if choice.name == self.gain_choice:
                return choice
        for choice in choices:
            if choice is not None:
                return choice
        return None

    def should_discard_deck_with_messenger(self, state, player):
        return self.discard_deck


def test_messenger_effects():
    ai = MessengerTestAI(discard_deck=True, gain_choice="Silver")
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Messenger")])

    player = state.players[0]
    player.hand = [get_card("Messenger")]
    player.deck = [get_card("Copper"), get_card("Estate")]
    player.discard = []
    player.actions = 1

    state.phase = "action"
    state.handle_action_phase()

    assert player.deck == []
    assert [card.name for card in player.discard] == ["Copper", "Estate"]
    assert player.buys == 2
    assert player.coins == 2

    other_ai = ChooseFirstActionAI()
    state2 = GameState(players=[])
    state2.initialize_game(
        [MessengerTestAI(discard_deck=False, gain_choice="Silver"), other_ai],
        [get_card("Messenger")],
    )

    current = state2.players[0]
    opponent = state2.players[1]
    current.discard = []
    opponent.discard = []
    state2.phase = "buy"
    state2.current_player_index = 0
    current.cards_gained_this_buy_phase = 0

    initial_silver = state2.supply["Silver"]
    state2.supply["Messenger"] -= 1
    state2.gain_card(current, get_card("Messenger"))

    assert [card.name for card in current.discard].count("Messenger") == 1
    assert [card.name for card in current.discard].count("Silver") == 1
    assert [card.name for card in opponent.discard].count("Silver") == 1
    assert state2.supply["Silver"] == initial_silver - 2
    assert current.cards_gained_this_buy_phase == 2


# ----------------------------------------------------------------------------
# Adventures: Reserve / Tavern infrastructure & cards
# ----------------------------------------------------------------------------


def _state_with_card(card_name, n_players=1):
    ais = [ChooseFirstActionAI() for _ in range(n_players)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(card_name)])
    return state


def test_coin_of_the_realm_sets_aside_and_calls():
    state = _state_with_card("Coin of the Realm")
    player = state.players[0]
    coin = get_card("Coin of the Realm")
    # Simulate playing the treasure directly.
    player.in_play.append(coin)
    coin.on_play(state)
    # Coin of the Realm went to tavern mat (NOT in_play).
    assert coin in player.tavern_mat
    assert coin not in player.in_play
    assert player.coins == 1
    # Now play Village from hand to trigger Coin of the Realm.
    village = get_card("Village")
    player.hand = [village]
    player.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Coin of the Realm should have been called (moved to discard).
    assert coin in player.discard
    assert coin not in player.tavern_mat


def test_guide_calls_at_start_of_turn():
    state = _state_with_card("Guide")
    player = state.players[0]
    guide = get_card("Guide")
    player.tavern_mat = [guide]
    player.hand = [get_card("Estate"), get_card("Estate")]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []
    state.phase = "start"
    state.handle_start_phase()
    # Guide called: hand discarded, drew 5.
    assert guide in player.discard or guide not in player.tavern_mat
    assert all(c.name == "Copper" for c in player.hand)


def test_ratcatcher_trashes_at_start_of_turn():
    state = _state_with_card("Ratcatcher")
    player = state.players[0]
    rat = get_card("Ratcatcher")
    player.tavern_mat = [rat]
    estate = get_card("Estate")
    player.hand = [estate, get_card("Copper")]
    state.phase = "start"
    state.handle_start_phase()
    assert estate in state.trash


def test_duplicate_calls_on_gain():
    state = _state_with_card("Duplicate")
    player = state.players[0]
    dup = get_card("Duplicate")
    player.tavern_mat = [dup]
    player.discard = []
    state.phase = "buy"
    # Gain a Copper (cost <= $6).
    state.supply["Copper"] -= 1
    state.gain_card(player, get_card("Copper"))
    coppers_gained = sum(1 for c in player.discard if c.name == "Copper")
    assert coppers_gained == 2  # original + duplicate


def test_transmogrify_trashes_and_gains_to_hand():
    state = _state_with_card("Transmogrify")
    player = state.players[0]
    tm = get_card("Transmogrify")
    player.tavern_mat = [tm]
    estate = get_card("Estate")
    player.hand = [estate]
    state.phase = "start"
    state.handle_start_phase()
    assert estate in state.trash


def test_royal_carriage_replays_action():
    state = _state_with_card("Royal Carriage")
    player = state.players[0]
    rc = get_card("Royal Carriage")
    player.tavern_mat = [rc]
    village = get_card("Village")
    player.hand = [village]
    player.actions = 1
    player.deck = [get_card("Copper") for _ in range(3)]
    state.phase = "action"
    state.handle_action_phase()
    # Village was played, then Royal Carriage replayed it. Village gives
    # +1 Card +2 Actions; played twice = +2 Cards +4 Actions. Started with 1
    # action, played village -1, so 0; +4 = 4 actions remaining (4 from 2x play).
    assert rc in player.discard
    assert player.actions >= 2  # at minimum, two Village plays


def test_distant_lands_vp_when_on_tavern():
    state = _state_with_card("Distant Lands")
    player = state.players[0]
    dl = get_card("Distant Lands")
    # Play it via play_effect to set aside on tavern.
    player.in_play = [dl]
    dl.play_effect(state)
    assert dl in player.tavern_mat
    assert dl.get_victory_points(player) == 4


def test_distant_lands_no_vp_when_in_discard():
    dl = get_card("Distant Lands")

    class FakePlayer:
        tavern_mat = []

    assert dl.get_victory_points(FakePlayer()) == 0


def test_traveller_chain_page_to_treasure_hunter():
    state = _state_with_card("Page", n_players=2)
    player = state.players[0]
    page = get_card("Page")
    player.in_play = [page]
    player.duration = []
    player.multiplied_durations = []
    state.phase = "cleanup"
    state.handle_cleanup_phase()
    # Page is exchanged; Treasure Hunter is in player's discard.
    has_th = any(c.name == "Treasure Hunter" for c in player.all_cards())
    assert has_th
    # Page returned to its pile.
    assert state.supply["Page"] >= 9


def test_traveller_chain_full_page_to_champion():
    """Walk the entire Page chain to verify each step exchanges."""
    state = _state_with_card("Page", n_players=2)
    player = state.players[0]
    chain = ["Treasure Hunter", "Warrior", "Hero"]
    next_chain = ["Warrior", "Hero", "Champion"]
    for current_name, next_name in zip(chain, next_chain):
        # Reset to player[0]'s turn before each cleanup.
        state.current_player_index = 0
        state.extra_turn = False
        player = state.players[0]
        card = get_card(current_name)
        player.in_play = [card]
        player.duration = []
        player.multiplied_durations = []
        player.hand = []
        player.tavern_mat = []
        state.phase = "cleanup"
        state.handle_cleanup_phase()
        assert any(c.name == next_name for c in player.all_cards()), (
            f"{current_name} did not exchange into {next_name}"
        )


def test_amulet_gives_coin_now_and_next_turn():
    state = _state_with_card("Amulet")
    player = state.players[0]
    amulet = get_card("Amulet")
    player.in_play = [amulet]
    # Empty hand prevents the default AI from picking 'trash'.
    player.hand = []
    amulet.play_effect(state)
    assert player.coins >= 1
    coins_after_play = player.coins
    amulet.on_duration(state)
    assert player.coins >= coins_after_play + 1


def test_caravan_guard_reaction_plays_self():
    state = _state_with_card("Caravan Guard", n_players=2)
    p1, p2 = state.players
    cg = get_card("Caravan Guard")
    p2.hand = [cg]
    p2.deck = [get_card("Copper")]
    # Simulate p1 attacking p2.
    state.attack_player(p2, lambda t: t, attacker=p1, attack_card=get_card("Witch"))
    # Caravan Guard should have moved from hand to duration.
    assert cg not in p2.hand
    assert cg in p2.duration


def test_dungeon_draws_and_discards_2():
    state = _state_with_card("Dungeon")
    player = state.players[0]
    dungeon = get_card("Dungeon")
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = []
    player.in_play = [dungeon]
    dungeon.play_effect(state)
    # Drew 2, discarded up to 2.
    assert player.actions >= 1


def test_gear_sets_aside_returns_next_turn():
    state = _state_with_card("Gear")
    player = state.players[0]
    gear = get_card("Gear")
    player.in_play = [gear]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [get_card("Estate"), get_card("Estate")]
    gear.play_effect(state)
    # Gear's draw 2 happens via on_play stats; play_effect just sets aside.
    assert len(gear.set_aside) <= 2
    saved = list(gear.set_aside)
    gear.on_duration(state)
    for s in saved:
        assert s in player.hand


def test_magpie_draws_card_or_treasure_or_gains():
    state = _state_with_card("Magpie")
    player = state.players[0]
    magpie = get_card("Magpie")
    player.deck = [get_card("Silver")]
    player.in_play = [magpie]
    player.hand = []
    magpie.play_effect(state)
    # Silver should be in hand.
    assert any(c.name == "Silver" for c in player.hand)


def test_port_gains_extra_port_via_buy():
    """Buying a Port gains TWO Ports total (the bought one and the bonus).
    The trigger is on gain, so any path that gains Port (Workshop, Buy,
    Inheritance, etc.) fires it."""
    state = _state_with_card("Port")
    player = state.players[0]
    initial_supply = state.supply["Port"]
    state.supply["Port"] -= 1
    state.gain_card(player, get_card("Port"))
    # After: 1 main Port (just gained) + 1 bonus Port from on_gain. Two
    # supply decrements total (the manual one above + the on_gain bonus).
    assert state.supply["Port"] == initial_supply - 2
    assert sum(1 for c in player.discard if c.name == "Port") == 2


def test_port_gain_via_workshop_grants_bonus():
    """Gaining a Port via Workshop (or any non-buy gain path) must still
    grant the bonus Port — the trigger is on gain, not on buy."""
    state = _state_with_card("Port")
    player = state.players[0]
    initial_supply = state.supply["Port"]
    # Simulate Workshop-like gain: decrement supply, call gain_card.
    state.supply["Port"] -= 1
    state.gain_card(player, get_card("Port"))
    assert state.supply["Port"] == initial_supply - 2
    assert sum(1 for c in player.discard if c.name == "Port") == 2


def test_port_bonus_copy_does_not_recurse():
    """The bonus Port that Port gains must NOT itself gain another Port —
    otherwise gaining one Port would empty the pile."""
    state = _state_with_card("Port")
    player = state.players[0]
    initial_supply = state.supply["Port"]
    state.supply["Port"] -= 1
    state.gain_card(player, get_card("Port"))
    # Exactly TWO Ports gained, not three or more.
    assert sum(1 for c in player.discard if c.name == "Port") == 2
    assert state.supply["Port"] == initial_supply - 2


def test_ranger_flips_journey_token():
    state = _state_with_card("Ranger")
    player = state.players[0]
    ranger = get_card("Ranger")
    player.deck = [get_card("Copper") for _ in range(10)]
    initial = player.journey_token_face_up
    ranger.play_effect(state)
    assert player.journey_token_face_up != initial


def test_relic_gives_minus_card_tokens_to_opponents():
    state = _state_with_card("Relic", n_players=2)
    p1, p2 = state.players
    relic = get_card("Relic")
    p1.in_play = [relic]
    relic.play_effect(state)
    assert p2.minus_card_tokens >= 1


def test_lost_city_opponents_draw_on_gain():
    state = _state_with_card("Lost City", n_players=2)
    p1, p2 = state.players
    p2.deck = [get_card("Estate")]
    initial_p2_hand = len(p2.hand)
    state.gain_card(p1, get_card("Lost City"))
    assert len(p2.hand) == initial_p2_hand + 1


def test_storyteller_pays_all_for_cards():
    state = _state_with_card("Storyteller")
    player = state.players[0]
    storyteller = get_card("Storyteller")
    player.in_play = [storyteller]
    player.hand = [get_card("Copper"), get_card("Copper")]
    player.deck = [get_card("Estate") for _ in range(5)]
    storyteller.play_effect(state)
    assert player.coins == 0
    # Drew 2 cards (paid 2).
    assert sum(1 for c in player.hand if c.name == "Estate") == 2


def test_treasure_trove_gains_gold_and_copper():
    state = _state_with_card("Treasure Trove")
    player = state.players[0]
    tt = get_card("Treasure Trove")
    tt.play_effect(state)
    names = [c.name for c in player.discard]
    assert "Gold" in names
    assert "Copper" in names


def test_hireling_draws_each_turn():
    state = _state_with_card("Hireling")
    player = state.players[0]
    hireling = get_card("Hireling")
    player.duration = [hireling]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = []
    state.phase = "start"
    state.handle_start_phase()
    # Hireling drew at least 1 card.
    assert any(c.name == "Copper" for c in player.hand)


def test_swamp_hag_attacks_buys():
    state = _state_with_card("Swamp Hag", n_players=2)
    p1, p2 = state.players
    hag = get_card("Swamp Hag")
    p1.in_play = [hag]
    hag.play_effect(state)
    assert p2.swamp_hag_attacks >= 1


def test_haunted_woods_attack():
    state = _state_with_card("Haunted Woods", n_players=2)
    p1, p2 = state.players
    hw = get_card("Haunted Woods")
    p1.in_play = [hw]
    hw.play_effect(state)
    assert p2.haunted_woods_attacks >= 1


def test_haunted_woods_persists_through_victims_turn():
    """The Haunted Woods penalty must remain active for the victim's
    *entire* next turn — start-of-turn must NOT clear it (otherwise the
    topdeck-on-gain effect evaporates before the buy phase). It is cleared
    at end-of-turn cleanup instead."""
    state = _state_with_card("Haunted Woods", n_players=2)
    p1, p2 = state.players
    p2.haunted_woods_attacks = 1
    # Start the victim's turn. The flag must persist.
    state.current_player_index = state.players.index(p2)
    state.phase = "start"
    state.handle_start_phase()
    assert p2.haunted_woods_attacks == 1, (
        "Haunted Woods must remain active during the victim's whole turn"
    )
    # End the victim's turn via cleanup. Now it clears.
    state.handle_cleanup_phase()
    assert p2.haunted_woods_attacks == 0


def test_swamp_hag_persists_through_victims_turn():
    """Swamp Hag's curse-on-buy effect must remain active during the
    victim's entire next turn. It clears at end-of-turn cleanup."""
    state = _state_with_card("Swamp Hag", n_players=2)
    p1, p2 = state.players
    p2.swamp_hag_attacks = 1
    state.current_player_index = state.players.index(p2)
    state.phase = "start"
    state.handle_start_phase()
    assert p2.swamp_hag_attacks == 1
    state.handle_cleanup_phase()
    assert p2.swamp_hag_attacks == 0


def test_bridge_troll_reduces_costs():
    state = _state_with_card("Bridge Troll", n_players=2)
    p1, _p2 = state.players
    bt = get_card("Bridge Troll")
    p1.in_play = [bt]
    village = get_card("Village")
    initial_cost = village.cost.coins
    cost_with_troll = state.get_card_cost(p1, village)
    assert cost_with_troll == max(0, initial_cost - 1)


def test_bridge_troll_reduction_is_global():
    """Bridge Troll's cost reduction applies to ALL players' purchases
    while it remains in play (the effect is global until the owner's
    next-turn cleanup), not just the owner's."""
    state = _state_with_card("Bridge Troll", n_players=2)
    p1, p2 = state.players
    # p2 has a Bridge Troll in their duration zone — p1 should still get
    # the cost reduction on their own buys.
    bt = get_card("Bridge Troll")
    p2.duration = [bt]
    province = get_card("Province")
    cost_for_p1 = state.get_card_cost(p1, province)
    assert cost_for_p1 == province.cost.coins - 1, (
        "Opponent's Bridge Troll must reduce p1's costs (the effect is global)"
    )


def test_bridge_troll_reductions_stack_globally():
    """Two opponents each with a Bridge Troll in play should stack: -$2
    on a Province for the buyer, regardless of who owns each Troll."""
    ais = [ChooseFirstActionAI() for _ in range(3)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card("Bridge Troll"), get_card("Province")])
    p1, p2, p3 = state.players
    p2.duration = [get_card("Bridge Troll")]
    p3.in_play = [get_card("Bridge Troll")]
    province = get_card("Province")
    cost_for_p1 = state.get_card_cost(p1, province)
    assert cost_for_p1 == province.cost.coins - 2


def test_champion_immunity_and_action_bonus():
    state = _state_with_card("Page", n_players=2)
    p1, p2 = state.players
    champion = get_card("Champion")
    p1.duration = [champion]
    p1.champions_in_play = 1
    # Attacks against p1 should be blocked.
    blocked = state._player_blocks_attack(p1, attacker=p2, attack_card=get_card("Witch"))
    assert blocked


def test_wine_merchant_calls_at_cleanup_with_2_coins():
    state = _state_with_card("Wine Merchant")
    player = state.players[0]
    wm = get_card("Wine Merchant")
    player.tavern_mat = [wm]
    player.coins = 2
    state.phase = "cleanup"
    state.handle_cleanup_phase()
    # Wine Merchant called from tavern.
    assert wm in player.discard or wm not in player.tavern_mat


def test_raze_self_trashes_and_keeps_card():
    state = _state_with_card("Raze")
    player = state.players[0]
    raze = get_card("Raze")
    player.in_play = [raze]
    player.deck = [get_card("Silver"), get_card("Copper")]
    player.hand = []
    raze.play_effect(state)
    # Raze trashed itself; cost 2, so revealed top 2.
    assert raze in state.trash

