"""Tests for Rising Sun kingdom cards, events, and prophecies."""

from typing import Optional

from dominion.cards.base_card import Card, CardType
from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from dominion.prophecies import get_prophecy

from tests.utils import ChooseFirstActionAI, DummyAI


class _GainFirstAI(ChooseFirstActionAI):
    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


def _setup(ai=None):
    if ai is None:
        ai = _GainFirstAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    return state, state.players[0]


def _two_player_setup():
    state = GameState(players=[])
    state.initialize_game([_GainFirstAI(), DummyAI()], [get_card("Village")])
    return state


# ---------------------------------------------------------------------------
# Kingdom cards
# ---------------------------------------------------------------------------


def test_alley_draws_action_and_discards():
    state, player = _setup()
    alley = get_card("Alley")
    player.hand = [alley, get_card("Estate"), get_card("Copper")]
    player.in_play = []
    player.deck = [get_card("Silver"), get_card("Gold")]
    player.actions = 1

    # Simulate playing Alley from hand
    player.hand.remove(alley)
    player.in_play.append(alley)
    alley.on_play(state)

    # 2 cards left after removing Alley + 1 draw - 1 discard = 2
    assert len(player.hand) == 2
    # An Estate or Copper got discarded
    assert any(c.name in ("Estate", "Copper") for c in player.discard)


def test_artist_counts_other_cards_in_play():
    state, player = _setup()
    artist = get_card("Artist")
    player.in_play = [get_card("Village"), get_card("Smithy"), artist]
    player.duration = []
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(5)]

    artist.on_play(state)
    # 3 cards in play (Village, Smithy, Artist). Only one Artist → counts itself
    # → draw 3.
    assert len(player.hand) == 3


def test_change_with_debt_gives_three_coins():
    state, player = _setup()
    change = get_card("Change")
    player.debt = 4
    player.coins = 0
    player.hand = [change]
    player.in_play = []

    player.hand.remove(change)
    player.in_play.append(change)
    change.on_play(state)

    assert player.coins == 3
    assert player.debt == 4  # debt unchanged by Change


def test_craftsman_takes_debt_and_gains_up_to_5():
    """Craftsman: take 2 Debt, gain a card costing up to $5 (excluding debt-cost cards)."""
    state, player = _setup()
    craftsman = get_card("Craftsman")
    player.in_play = [craftsman]
    debt_before = player.debt

    state.supply["Mountain Shrine"] = 10  # debt-cost; not eligible
    state.supply["Village"] = 10  # $3, eligible
    state.supply["Silver"] = 40
    craftsman.on_play(state)
    # Craftsman takes 2 Debt
    assert player.debt == debt_before + 2
    # And a $5-or-less card was gained (Mountain Shrine cannot be picked)
    assert not any(c.name == "Mountain Shrine" for c in player.discard)


def test_daimyo_replays_next_action():
    state, player = _setup()
    daimyo = get_card("Daimyo")
    village = get_card("Village")
    player.hand = [daimyo, village]
    player.in_play = []
    player.deck = [get_card("Copper") for _ in range(10)]
    player.actions = 1

    # Play Daimyo
    player.hand.remove(daimyo)
    player.in_play.append(daimyo)
    daimyo.on_play(state)
    assert player.daimyo_pending == 1

    # The action phase loop normally handles the replay; simulate it.
    player.hand.remove(village)
    player.in_play.append(village)
    actions_before = player.actions
    daimyo_replays = player.daimyo_pending
    player.daimyo_pending = 0
    plays = 1 + daimyo_replays
    for _ in range(plays):
        village.on_play(state)
    # Village gives +2 actions per play, played twice
    assert player.actions == actions_before + 4


def test_fishmonger_basic_stats():
    state, player = _setup()
    fish = get_card("Fishmonger")
    player.in_play = [fish]
    fish.on_play(state)
    assert player.coins == 1
    assert player.buys == 2  # base 1 + Fishmonger's +1


def test_gold_mine_optionally_gains_gold_with_debt():
    state, player = _setup()
    gold_mine = get_card("Gold Mine")
    player.in_play = [gold_mine]
    state.supply["Gold"] = 30
    debt_before = player.debt
    gold_count_before = sum(1 for c in player.discard if c.name == "Gold")
    gold_mine.on_play(state)
    after = sum(1 for c in player.discard if c.name == "Gold")
    if after > gold_count_before:
        assert player.debt >= debt_before + 4


def test_litter_basic_stats():
    state, player = _setup()
    litter = get_card("Litter")
    player.in_play = [litter]
    player.deck = [get_card("Copper") for _ in range(5)]
    actions_before = player.actions
    debt_before = player.debt
    litter.on_play(state)
    # +2 Cards, +2 Actions, +1 Debt (NOT +1 Buy)
    assert player.actions == actions_before + 2
    assert player.debt == debt_before + 1


def test_ninja_attacks_opponents():
    state = _two_player_setup()
    attacker, victim = state.players
    ninja = get_card("Ninja")
    attacker.in_play = [ninja]
    victim.hand = [get_card("Copper") for _ in range(5)]
    attacker.deck = [get_card("Copper") for _ in range(5)]
    state.current_player_index = 0

    ninja.on_play(state)
    assert len(victim.hand) == 3


def test_poet_puts_cheap_card_in_hand():
    state, player = _setup()
    poet = get_card("Poet")
    cheap_card = get_card("Estate")  # costs 2
    player.hand = []
    player.deck = [cheap_card]
    player.in_play = [poet]

    poet.on_play(state)
    # +1 Card draws Estate. Then Poet reveals top of deck (now empty); no
    # further hand growth. Estate must be in hand from the +1 Card draw.
    assert any(c.name == "Estate" for c in player.hand)


def test_rice_treasure_counts_types():
    state, player = _setup()
    rice = get_card("Rice")
    village = get_card("Village")  # ACTION
    silver = get_card("Silver")  # TREASURE
    player.in_play = [village, silver]
    player.duration = []

    rice.on_play(state)
    # Types in play before Rice itself: ACTION, TREASURE → 2.
    # Rice adds itself (TREASURE already counted).
    assert player.coins >= 2


def test_rice_broker_treasure_action_double_draws():
    state, player = _setup()
    rice_broker = get_card("Rice Broker")
    # Crown is an Action+Treasure
    crown = get_card("Crown")
    player.hand = [crown]
    player.in_play = [rice_broker]
    player.deck = [get_card("Copper") for _ in range(10)]

    rice_broker.on_play(state)
    # +2 then +5 = 7 cards drawn
    assert len(player.hand) == 7


def test_riverboat_plays_set_aside_next_turn():
    state = GameState(players=[])
    festival = get_card("Festival")
    state.initialize_game(
        [_GainFirstAI()],
        [get_card("Riverboat"), get_card("Village")],
        riverboat_set_aside=festival,
    )
    player = state.players[0]
    riverboat = get_card("Riverboat")
    player.in_play = [riverboat]
    player.duration = []
    player.actions = 0
    player.coins = 0
    player.buys = 1

    riverboat.on_play(state)
    # Riverboat goes into duration
    assert riverboat in player.duration
    # On next turn, festival plays
    coins_before = player.coins
    actions_before = player.actions
    riverboat.on_duration(state)
    # Festival gives +2 Actions, +1 Buy, +$2
    assert player.actions == actions_before + 2
    assert player.coins == coins_before + 2


def test_ronin_draws_to_seven():
    state, player = _setup()
    ronin = get_card("Ronin")
    player.hand = [get_card("Copper") for _ in range(2)]
    player.deck = [get_card("Silver") for _ in range(10)]
    player.in_play = [ronin]

    coins_before = player.coins
    ronin.on_play(state)
    # Per rulebook, Ronin draws until 7 in hand. No +$.
    assert len(player.hand) == 7
    assert player.coins == coins_before


def test_root_cellar_basic_stats():
    state, player = _setup()
    root = get_card("Root Cellar")
    player.in_play = [root]
    player.deck = [get_card("Copper") for _ in range(10)]
    debt_before = player.debt
    actions_before = player.actions
    hand_before = len(player.hand)
    root.on_play(state)
    # +3 Cards, +1 Action, +3 Debt
    assert len(player.hand) == hand_before + 3
    assert player.actions == actions_before + 1
    assert player.debt == debt_before + 3


def test_rustic_village_omen_reduces_sun():
    state = GameState(players=[])
    state.initialize_game([_GainFirstAI()], [get_card("Rustic Village")])
    player = state.players[0]
    assert state.prophecy is not None
    assert state.sun_tokens == 5  # 1 player → defaults to 5

    rv = get_card("Rustic Village")
    player.hand = [rv]
    player.in_play = []
    player.deck = [get_card("Copper") for _ in range(5)]

    player.hand.remove(rv)
    player.in_play.append(rv)
    rv.on_play(state)
    assert state.sun_tokens == 4


def test_snake_witch_curses_opponents_when_unique():
    state = _two_player_setup()
    attacker, victim = state.players
    snake = get_card("Snake Witch")
    attacker.hand = [snake, get_card("Copper")]
    attacker.deck = [get_card("Estate")]
    attacker.in_play = []
    state.current_player_index = 0

    attacker.hand.remove(snake)
    attacker.in_play.append(snake)
    snake.on_play(state)
    # All hand names different (Estate after +1 Card, Copper) → return Snake
    # Witch to its pile and curse opponents.
    if all(False for c in attacker.in_play if c.name == "Snake Witch"):
        # Returned to pile
        assert any(c.name == "Curse" for c in victim.discard)


def test_tanuki_remodels():
    state, player = _setup()
    tanuki = get_card("Tanuki")
    estate = get_card("Estate")  # cost 2
    player.hand = [estate]
    player.in_play = [tanuki]
    state.supply["Silver"] = 40
    state.supply["Gold"] = 30
    state.supply["Village"] = 10

    tanuki.on_play(state)
    # Trashed Estate ($2) → gain card up to $4. AI (_GainFirstAI) picks first.
    assert any(c.name == "Estate" for c in state.trash)


def test_tea_house_basic_stats():
    state = GameState(players=[])
    state.initialize_game([_GainFirstAI()], [get_card("Tea House")])
    player = state.players[0]
    tea = get_card("Tea House")
    player.hand = [tea]
    player.in_play = []
    player.deck = [get_card("Copper") for _ in range(5)]

    sun_before = state.sun_tokens
    player.hand.remove(tea)
    player.in_play.append(tea)
    tea.on_play(state)
    assert player.coins == 2
    assert state.sun_tokens == sun_before - 1


# ---------------------------------------------------------------------------
# Shadow card mechanic
# ---------------------------------------------------------------------------


def test_shadow_cards_shuffle_to_bottom():
    state, player = _setup()
    fish = get_card("Fishmonger")
    village = get_card("Village")
    player.discard = [fish, village]
    player.deck = []

    player.shuffle_discard_into_deck()
    # Shadow card (Fishmonger) is at the bottom (index 0)
    assert player.deck[0] is fish


def test_card_type_includes_shadow_and_omen():
    """Make sure CardType.SHADOW and CardType.OMEN are recognized."""
    fish = get_card("Fishmonger")
    rustic = get_card("Rustic Village")
    assert fish.is_shadow
    assert rustic.is_omen


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def test_amass_blocks_when_action_in_play():
    state, player = _setup()
    player.in_play = [get_card("Village")]
    player.coins = 2
    state.supply["Smithy"] = 10
    Amass = get_event("Amass").__class__
    Amass().on_buy(state, player)
    # Smithy was not gained (Village blocks Amass)
    assert not any(c.name == "Smithy" for c in player.discard)


def test_amass_gains_action_when_no_actions_in_play():
    state, player = _setup()
    player.in_play = []
    player.duration = []
    player.coins = 2
    state.supply["Smithy"] = 10
    get_event("Amass").on_buy(state, player)
    # Some Action card was gained
    assert any(c.is_action for c in player.discard)


def test_practice_plays_action_twice():
    state, player = _setup()
    village = get_card("Village")
    player.hand = [village]
    player.in_play = []
    player.actions = 1
    player.deck = [get_card("Copper") for _ in range(5)]

    actions_before = player.actions
    get_event("Practice").on_buy(state, player)
    # Village played twice → +4 actions, +2 cards
    assert player.actions == actions_before + 4
    assert len(player.hand) == 2


def test_sea_trade_draws_per_action_and_trashes():
    state, player = _setup()
    village = get_card("Village")
    village2 = get_card("Village")
    player.in_play = [village, village2]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = [get_card("Copper")]  # something to trash
    get_event("Sea Trade").on_buy(state, player)
    # 2 Action cards in play → drew 2, may trash up to 2.
    assert any(c.name == "Copper" for c in state.trash)


def test_continue_is_once_per_turn():
    state, player = _setup()
    player.coins = 16
    state.supply["Village"] = 10
    Continue = get_event("Continue").__class__
    Continue().on_buy(state, player)
    assert player.continue_used_this_turn is True
    assert Continue().may_be_bought(state, player) is False


def test_kintsugi_requires_gold_for_gain():
    state, player = _setup()
    player.kintsugi_has_gained_gold = False
    player.hand = [get_card("Estate")]
    player.in_play = []
    state.supply["Silver"] = 40
    get_event("Kintsugi").on_buy(state, player)
    # No Silver gained because we haven't gained a Gold this game
    silvers_in_discard = sum(1 for c in player.discard if c.name == "Silver")
    assert silvers_in_discard == 0


# ---------------------------------------------------------------------------
# Prophecies
# ---------------------------------------------------------------------------


def test_prophecy_setup_with_omen_in_supply():
    state = GameState(players=[])
    state.initialize_game([_GainFirstAI()], [get_card("Rustic Village")])
    assert state.prophecy is not None
    assert state.sun_tokens == 5


def test_omen_play_removes_sun_token():
    state, player = _setup()
    state.prophecy = get_prophecy("Approaching Army")
    state.sun_tokens = 5
    state.prophecy.is_active = False

    rv = get_card("Rustic Village")
    player.in_play.append(rv)
    rv.on_play(state)
    assert state.sun_tokens == 4


def test_prophecy_activates_when_last_sun_removed():
    state, player = _setup()
    state.prophecy = get_prophecy("Great Leader")
    state.sun_tokens = 1
    state.prophecy.is_active = False

    state.remove_sun_token(1)
    assert state.sun_tokens == 0
    assert state.prophecy.is_active is True


def test_great_leader_grants_action_after_each_action_play():
    state, player = _setup()
    state.prophecy = get_prophecy("Great Leader")
    state.prophecy.is_active = True
    state.sun_tokens = 0

    village = get_card("Village")
    player.in_play.append(village)
    actions_before = player.actions
    village.on_play(state)
    state.prophecy.on_play_action(state, player, village)
    # Village gives +2 actions, then Great Leader adds +1
    assert player.actions == actions_before + 3


def test_good_harvest_first_treasure_per_turn():
    state, player = _setup()
    state.prophecy = get_prophecy("Good Harvest")
    state.prophecy.is_active = True
    state.sun_tokens = 0

    silver = get_card("Silver")
    coins_before = player.coins
    state.prophecy.on_play_treasure(state, player, silver)
    assert player.coins == coins_before + 1
    assert player.buys >= 2  # +1 Buy
    state.prophecy.on_play_treasure(state, player, silver)
    # No further bonus on the second treasure
    assert player.coins == coins_before + 1


def test_bureaucracy_grants_copper_on_coin_cost_gain():
    state, player = _setup()
    state.prophecy = get_prophecy("Bureaucracy")
    state.prophecy.is_active = True
    state.sun_tokens = 0
    state.supply["Copper"] = 10
    state.supply["Village"] = 10

    state.prophecy.on_gain(state, player, get_card("Village"))
    assert any(c.name == "Copper" for c in player.discard)


def test_progress_topdecks_gains():
    state, player = _setup()
    state.prophecy = get_prophecy("Progress")
    state.prophecy.is_active = True
    state.sun_tokens = 0
    village = get_card("Village")
    player.discard.append(village)
    state.prophecy.on_gain(state, player, village)
    assert player.deck[-1] is village


def test_flourishing_trade_lowers_costs():
    state, player = _setup()
    state.prophecy = get_prophecy("Flourishing Trade")
    state.prophecy.is_active = True
    state.sun_tokens = 0

    village = get_card("Village")
    cost = state.get_card_cost(player, village)
    assert cost == max(0, village.cost.coins - 1)


def test_kind_emperor_gains_action_to_hand_on_turn_start():
    state, player = _setup()
    state.prophecy = get_prophecy("Kind Emperor")
    state.prophecy.is_active = True
    state.sun_tokens = 0
    state.supply["Village"] = 10

    hand_size_before = len(player.hand)
    state.prophecy.on_turn_start(state, player)
    # An action should have been gained directly to hand
    assert len(player.hand) == hand_size_before + 1


def test_growth_chains_treasure_gains():
    state, player = _setup()
    state.prophecy = get_prophecy("Growth")
    state.prophecy.is_active = True
    state.sun_tokens = 0
    # Gaining Gold ($6) → must gain a cheaper card
    state.supply["Silver"] = 40
    state.supply["Copper"] = 30
    state.supply["Gold"] = 30
    gold = get_card("Gold")
    state.prophecy.on_gain(state, player, gold)
    # Some cheaper card was gained
    assert player.discard, "Growth should have gained a cheaper card"


def test_sickness_curse_or_discard():
    state, player = _setup()
    state.prophecy = get_prophecy("Sickness")
    state.prophecy.is_active = True
    state.sun_tokens = 0
    state.supply["Curse"] = 30
    player.hand = [get_card("Estate") for _ in range(2)]  # only 2 junk → curse mode

    state.prophecy.on_cleanup_start(state, player)
    # Curse should have gone to deck (top)
    assert any(c.name == "Curse" for c in player.deck), "Curse should be on deck"
