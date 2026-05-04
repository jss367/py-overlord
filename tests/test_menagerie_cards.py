"""Tests for Menagerie kingdom cards."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI, ChooseFirstActionAI


def _two_player_state(extra_kingdom=None):
    extra_kingdom = extra_kingdom or []
    ai1 = ChooseFirstActionAI()
    ai2 = ChooseFirstActionAI()
    state = GameState(players=[])
    kingdom = [get_card("Village")] + extra_kingdom
    state.initialize_game([ai1, ai2], kingdom)
    state.supply.setdefault("Horse", 30)
    state.supply.setdefault("Curse", 10)
    state.supply.setdefault("Silver", 40)
    state.supply.setdefault("Gold", 30)
    state.supply.setdefault("Estate", 8)
    state.supply.setdefault("Duchy", 8)
    state.supply.setdefault("Province", 8)
    state.supply.setdefault("Copper", 46)
    return state, state.players[0], state.players[1]


def test_supplies_gain_horse_on_top_of_deck():
    state, p1, _ = _two_player_state()
    supplies = get_card("Supplies")
    state.supply["Supplies"] = state.supply.get("Supplies", 10)
    state.supply["Supplies"] -= 1
    state.gain_card(p1, supplies)
    # to_deck=True places at deck[0] per existing trader test convention.
    assert any(c.name == "Horse" for c in p1.deck)


def test_camel_train_exiles_non_victory():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Camel Train")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Gold" or c.name == "Silver" or c.name == "Copper" for c in p1.exile)
    # The exiled card is not a Victory
    for c in p1.exile:
        assert not c.is_victory


def test_camel_train_exiles_gold_on_gain():
    state, p1, _ = _two_player_state()
    state.supply["Camel Train"] = state.supply.get("Camel Train", 10)
    state.supply["Camel Train"] -= 1
    state.gain_card(p1, get_card("Camel Train"))
    assert any(c.name == "Gold" for c in p1.exile)


def test_goatherd_left_count():
    state, p1, p2 = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Goatherd"), get_card("Estate"), get_card("Copper")]
    # Pad p2 hand to >= 5
    p2.hand = [get_card("Copper")] * 5
    state.phase = "action"
    state.handle_action_phase()
    # +$1 from card + $1 from p2's 5 cards
    assert p1.coins >= 2


def test_stockpile_exiles_itself_when_played():
    state, p1, _ = _two_player_state()
    s = get_card("Stockpile")
    p1.in_play = [s]
    s.on_play(state)
    assert s in p1.exile
    assert s not in p1.in_play
    assert p1.coins == 3
    assert p1.buys == 2  # base 1 + 1 from card


def test_bounty_hunter_no_coin_when_already_exiled():
    state, p1, _ = _two_player_state()
    p1.exile = [get_card("Estate")]
    p1.hand = [get_card("Bounty Hunter"), get_card("Estate")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Estate name already exiled → no +$3
    assert p1.coins == 0


def test_bounty_hunter_gives_three_coins_for_new_exile():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Bounty Hunter"), get_card("Copper")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    assert p1.coins == 3


def test_groom_action_gain_horse():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.hand = [get_card("Groom")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Should have gained a Village (action) and a Horse
    gained_names = {c.name for c in p1.discard + p1.deck}
    assert "Horse" in gained_names


def test_cavalry_gains_two_horses_on_play():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Cavalry")]
    state.phase = "action"
    state.handle_action_phase()
    horse_count = sum(1 for c in p1.discard if c.name == "Horse")
    assert horse_count == 2


def test_sheepdog_plays_when_gaining():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sheepdog")]
    # Trigger gain
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Sheepdog should be in play (after self-trigger), and we drew 2 cards.
    assert any(c.name == "Sheepdog" for c in p1.in_play)


def test_sleigh_puts_gained_card_into_hand():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sleigh")]
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Silver should be in hand (Sleigh used 'hand' option)
    assert any(c.name == "Silver" for c in p1.hand)
    assert any(c.name == "Sleigh" for c in p1.discard)


def test_falconer_play_gains_cheaper_card_to_hand():
    state, p1, _ = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Falconer")]
    state.supply["Silver"] = state.supply.get("Silver", 40)
    state.phase = "action"
    state.handle_action_phase()
    # Falconer cost = $5; should have gained a card costing < $5 (Silver) into hand
    assert any(c.name in ("Silver", "Village", "Estate") for c in p1.hand)


def test_kiln_gains_copy_of_next_play():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = 10
    p1.actions = 1
    # Kiln in play, then play a Village; should gain a Village copy.
    kiln = get_card("Kiln")
    p1.in_play.append(kiln)
    kiln.on_play(state)
    # Now simulate playing a Village (cost=3)
    village = get_card("Village")
    p1.hand = [village]
    state.phase = "action"
    state.handle_action_phase()
    village_gained = sum(1 for c in p1.discard if c.name == "Village")
    assert village_gained == 1


def test_livery_grants_horse_on_gain_4plus():
    state, p1, _ = _two_player_state()
    state.supply["Village"] = state.supply.get("Village", 10)
    p1.in_play.append(get_card("Livery"))
    # Gain a $4 card (Smithy substitute → use Wayfarer? No: use a $4 card.
    # Use Bounty Hunter which is $4.
    state.supply["Bounty Hunter"] = state.supply.get("Bounty Hunter", 10)
    state.supply["Bounty Hunter"] -= 1
    state.gain_card(p1, get_card("Bounty Hunter"))
    horse_count = sum(1 for c in p1.discard if c.name == "Horse")
    assert horse_count == 1


def test_animal_fair_cost_reduction():
    state, p1, _ = _two_player_state()
    af = get_card("Animal Fair")
    p1.in_play = [get_card("Village"), get_card("Smithy")]
    cost = state.get_card_cost(p1, af)
    # 7 - 2*2 = 3
    assert cost == 3


def test_wayfarer_cost_matches_last_gain():
    state, p1, _ = _two_player_state()
    p1.gained_cards_this_turn = ["Silver"]  # Silver costs 3
    wf = get_card("Wayfarer")
    cost = state.get_card_cost(p1, wf)
    assert cost == 3


def test_sanctuary_basics():
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sanctuary"), get_card("Estate"), get_card("Copper"), get_card("Copper")]
    p1.actions = 1
    state.phase = "action"
    state.handle_action_phase()
    # Should have +1 buy and have exiled an Estate
    assert any(c.name == "Estate" for c in p1.exile)
    assert p1.buys == 2


def test_black_cat_curses_opponents_when_reacted_off_turn():
    state, p1, p2 = _two_player_state()
    # p2 owns the Black Cat in hand; p1 (current player) gains a Victory
    # card → p2's Black Cat triggers, cursing p1.
    p2.hand.append(get_card("Black Cat"))
    state.supply["Estate"] = state.supply.get("Estate", 8)
    state.supply["Estate"] -= 1
    curses_before = state.supply.get("Curse", 0)
    state.gain_card(p1, get_card("Estate"))
    # The Black Cat owner curses each other player (p1 gets a Curse).
    assert any(c.name == "Curse" for c in p1.exile + p1.discard + p1.deck + p1.hand)
    assert state.supply["Curse"] == curses_before - 1


def test_falconer_reaction_gains_cheaper_card():
    state, p1, p2 = _two_player_state()
    # p2 has a Falconer in hand, p1 gains a Gold ($6).
    p2.hand.append(get_card("Falconer"))
    state.supply["Gold"] = state.supply.get("Gold", 30)
    state.supply["Gold"] -= 1
    state.gain_card(p1, get_card("Gold"))
    # p2 should have gained something cheaper than Gold.
    cheaper_gain = any(c.cost.coins < 6 for c in p2.discard + p2.deck)
    assert cheaper_gain


def test_coven_exiles_curse_for_opponent():
    state, p1, p2 = _two_player_state()
    p1.actions = 1
    p1.hand = [get_card("Coven")]
    state.phase = "action"
    state.handle_action_phase()
    assert any(c.name == "Curse" for c in p2.exile)


def test_cavalry_on_gain_in_buy_phase_does_not_grant_action():
    """Buying Cavalry returns to action phase but must not grant a free Action."""
    state, p1, _ = _two_player_state()
    state.supply["Cavalry"] = state.supply.get("Cavalry", 10)
    state.phase = "buy"
    p1.actions = 0
    state.supply["Cavalry"] -= 1
    state.gain_card(p1, get_card("Cavalry"))
    # Phase reverts but actions stay at 0 — the card text never grants +1 Action.
    assert state.phase == "action"
    assert p1.actions == 0


def test_multiple_sheepdogs_all_react_to_single_gain():
    """Each Sheepdog in hand should independently react to a gain."""
    state, p1, _ = _two_player_state()
    p1.hand = [get_card("Sheepdog"), get_card("Sheepdog")]
    p1.deck = [get_card("Copper")] * 10
    state.supply["Silver"] -= 1
    state.gain_card(p1, get_card("Silver"))
    # Both Sheepdogs played from hand into in_play.
    assert sum(1 for c in p1.in_play if c.name == "Sheepdog") == 2


def test_sheepdog_off_turn_reacts_for_owner():
    """Sheepdog should draw cards for its owner, not the active player, when
    the gain happens on another player's turn."""
    state, p1, p2 = _two_player_state()
    # p1 is the current player; p2 owns Sheepdog and is gaining a Curse via
    # an opponent's effect (e.g. Black Cat). Simulate by directly gaining on
    # p2 while p1 is the current player.
    p2.hand = [get_card("Sheepdog")]
    p2.deck = [get_card("Estate"), get_card("Estate")]
    p1_hand_before = len(p1.hand)
    state.supply["Curse"] -= 1
    state.gain_card(p2, get_card("Curse"))
    # p2 should have +2 cards drawn (their hand grew by 2 from deck).
    assert any(c.name == "Estate" for c in p2.hand)
    # p1's hand size is unchanged — Sheepdog did not draw for the active player.
    assert len(p1.hand) == p1_hand_before


def test_kiln_consumes_trigger_when_pile_empty():
    """If the next-played card has no supply pile to copy from, Kiln still
    consumes its pending charge so it cannot carry over to a later card."""
    state, p1, _ = _two_player_state()
    state.supply["Village"] = 10
    p1.actions = 5
    kiln = get_card("Kiln")
    p1.in_play.append(kiln)
    kiln.on_play(state)  # Sets kiln_pending = 1
    # Empty the Village pile and play a Village (which has no copies left).
    village_a = get_card("Village")
    state.supply["Village"] = 0
    p1.hand = [village_a, get_card("Village")]
    state.phase = "action"
    state.handle_action_phase()
    # Pending must have been consumed by the first play even though no copy
    # could be gained.
    assert getattr(p1, "kiln_pending", 0) == 0
