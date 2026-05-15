"""Tests for the Marchland promo card and the Summon promo event."""

from dominion.cards.registry import get_card
from dominion.events.registry import get_event
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


class _NoOpAlly:
    name = "No-op Ally"


def _new_state(kingdom_card_names=None):
    if kingdom_card_names is None:
        kingdom_card_names = ["Village", "Smithy"]
    ai = ChooseFirstActionAI()
    state = GameState(players=[])
    kingdom_cards = [get_card(n) for n in kingdom_card_names]
    allies = [_NoOpAlly()] if any(card.is_liaison for card in kingdom_cards) else None
    state.initialize_game([ai], kingdom_cards, allies=allies)
    return state


# --- Marchland --------------------------------------------------------------


def test_marchland_gives_buy_and_dollars_for_discards():
    state = _new_state()
    player = state.players[0]
    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Curse")]
    starting_buys = player.buys
    starting_coins = player.coins

    marchland = get_card("Marchland")
    player.in_play.append(marchland)
    marchland.on_play(state)

    assert player.buys == starting_buys + 1
    # All three default-low-priority cards should be discarded for $3.
    assert player.coins == starting_coins + 3
    assert player.hand == []
    discarded_names = sorted(c.name for c in player.discard)
    assert discarded_names == ["Copper", "Curse", "Estate"]


def test_marchland_with_empty_hand_just_gives_buy():
    state = _new_state()
    player = state.players[0]
    player.hand = []
    starting_buys = player.buys
    starting_coins = player.coins

    marchland = get_card("Marchland")
    player.in_play.append(marchland)
    marchland.on_play(state)

    assert player.buys == starting_buys + 1
    assert player.coins == starting_coins


def test_marchland_vp_is_one_per_three_victory_cards():
    state = _new_state()
    player = state.players[0]
    marchland = get_card("Marchland")
    # Replace deck with a controlled set: 7 victory cards + non-victory.
    player.hand = []
    player.discard = []
    player.in_play = []
    player.deck = (
        [get_card("Estate") for _ in range(4)]
        + [get_card("Duchy") for _ in range(2)]
        + [get_card("Province")]
        + [get_card("Copper") for _ in range(5)]
        + [marchland]  # Marchland itself counts (it's a Victory card).
    )
    # 4 + 2 + 1 + 1 (Marchland) = 8 victory cards => 8 // 3 = 2 VP.
    assert marchland.get_victory_points(player) == 2


def test_marchland_zero_vp_with_two_victory_cards():
    state = _new_state()
    player = state.players[0]
    marchland = get_card("Marchland")
    player.hand = []
    player.discard = []
    player.in_play = []
    # 1 Estate + Marchland = 2 victory cards => 2 // 3 = 0 VP.
    player.deck = [get_card("Estate"), marchland]
    assert marchland.get_victory_points(player) == 0


def test_marchland_is_action_and_victory():
    marchland = get_card("Marchland")
    assert marchland.is_action
    assert marchland.is_victory


# --- Summon -----------------------------------------------------------------


def test_summon_gains_action_and_sets_aside_for_next_turn():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)

    # Card is set aside, NOT in discard or deck.
    assert len(player.summon_set_aside) == 1
    set_aside = player.summon_set_aside[0]
    assert set_aside.is_action
    assert set_aside.cost.coins <= 4
    assert set_aside not in player.discard
    assert set_aside not in player.deck


def test_summon_skips_when_no_legal_action_in_supply():
    # A kingdom with no <=$4 Action: Smithy is $4, so include something
    # cheap-but-not-action only by suppressing supply.
    state = _new_state(["Smithy"])
    player = state.players[0]
    # Empty out every Action <= $4 from the supply.
    for name in list(state.supply.keys()):
        try:
            card = get_card(name)
        except Exception:
            continue
        if card.is_action and card.cost.coins <= 4:
            state.supply[name] = 0
    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert player.summon_set_aside == []


def test_summon_set_aside_card_plays_on_next_turn_start():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1
    set_aside = player.summon_set_aside[0]
    assert set_aside.name == "Village"

    # Drive a fresh start phase as if the next turn had begun.
    starting_actions = player.actions
    starting_hand_len = len(player.hand)
    state.phase = "start"
    state.handle_start_phase()

    # Village played: +1 Card, +2 Actions; the card lives in in_play now.
    assert player.summon_set_aside == []
    assert set_aside in player.in_play
    assert player.actions == starting_actions + 2
    assert len(player.hand) == starting_hand_len + 1


def test_summon_decrements_supply():
    state = _new_state(["Village"])
    player = state.players[0]
    before = state.supply["Village"]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    after = state.supply["Village"]
    assert after == before - 1


def test_summoned_card_is_owned_by_player_for_scoring():
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    set_aside = player.summon_set_aside[0]
    # The set-aside zone is part of the player's owned cards.
    assert set_aside in player.all_cards()


def test_summon_routes_gain_through_pipeline_so_on_gain_fires():
    """Summon must route through gain_card so on-gain hooks (Collection,
    Groundskeeper, projects, etc.) fire for the gained card.

    Collection gives +1 VP token whenever you gain an Action card while
    Collection has been played. Use it as a witness that on_gain fired.
    """
    state = _new_state(["Village"])
    player = state.players[0]
    player.collection_played = 1
    starting_vp = player.vp_tokens

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1
    assert player.vp_tokens == starting_vp + 1


def test_summon_uses_effective_cost_so_cost_reduction_widens_choices():
    """A $5 Action becomes Summon-eligible when the player has $1 of cost
    reduction, because Summon should filter on effective cost (not printed).
    """
    # Festival is $5 printed.
    state = _new_state(["Festival"])
    player = state.players[0]
    player.cost_reduction = 1

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1
    assert player.summon_set_aside[0].name == "Festival"


def test_summon_play_increments_actions_this_turn():
    """The Summon-played Action must count toward actions_this_turn so
    Conspirator and similar cards see the play (matching Hasty/Patient).
    """
    state = _new_state(["Village"])
    player = state.players[0]
    summon = get_event("Summon")
    summon.on_buy(state, player)
    starting_actions_count = player.actions_this_turn

    state.phase = "start"
    state.handle_start_phase()

    assert player.actions_this_turn == starting_actions_count + 1


def test_summon_topdeck_via_royal_seal_stays_on_deck():
    """If the gain was redirected to the deck (here via Royal Seal), the
    card must NOT be yanked off into Summon's set-aside zone — the
    player's chosen destination is honored.
    """
    state = _new_state(["Village"])
    player = state.players[0]
    royal_seal = get_card("Royal Seal")
    player.in_play.append(royal_seal)
    player.ai.should_topdeck_with_royal_seal = lambda s, p, c: True

    summon = get_event("Summon")
    starting_deck_size = len(player.deck)
    summon.on_buy(state, player)

    assert player.summon_set_aside == []
    assert len(player.deck) == starting_deck_size + 1
    assert player.deck[-1].name == "Village"


def test_summon_resolves_knights_pile_correctly():
    """Knights is an ordered pile: the placeholder name is "Knights" but the
    gainable card is the actual top knight (e.g. "Sir Bailey"). Summon
    must use top_of_pile and pop pile_order, not gain the placeholder.
    Knights are $5 normally, so apply $1 of cost reduction to make them
    Summon-eligible.
    """
    state = _new_state(["Knights"])
    player = state.players[0]
    player.cost_reduction = 1

    starting_supply = state.supply["Knights"]
    starting_order_len = len(state.pile_order["Knights"])
    expected_top_name = state.pile_order["Knights"][-1]

    summon = get_event("Summon")
    summon.on_buy(state, player)

    assert len(player.summon_set_aside) == 1
    gained = player.summon_set_aside[0]
    assert gained.is_knight
    assert gained.name == expected_top_name
    assert gained.name != "Knights"  # not the placeholder
    assert state.supply["Knights"] == starting_supply - 1
    assert len(state.pile_order["Knights"]) == starting_order_len - 1


def test_summon_exile_reclaim_on_knight_keeps_pile_intact():
    """If the Summoned Knight is reclaimed from Exile (a same-named copy
    is on the Exile mat), the Knights pile must NOT be consumed: pile_order
    keeps its top card and the supply count is restored.
    """
    state = _new_state(["Knights"])
    player = state.players[0]
    player.cost_reduction = 1
    top_knight_name = state.pile_order["Knights"][-1]
    # Pre-place the same-named knight on Exile.
    player.exile.append(get_card(top_knight_name))

    starting_supply = state.supply["Knights"]
    starting_order_len = len(state.pile_order["Knights"])

    summon = get_event("Summon")
    summon.on_buy(state, player)

    # Pile untouched.
    assert state.supply["Knights"] == starting_supply
    assert len(state.pile_order["Knights"]) == starting_order_len
    assert state.pile_order["Knights"][-1] == top_knight_name
    # Exile reclaimed — the previously-exiled instance is now in set-aside.
    assert player.exile == []
    assert len(player.summon_set_aside) == 1
    assert player.summon_set_aside[0].name == top_knight_name


def test_summon_changeling_exchange_on_knight_no_double_restore():
    """When Summon gains a Knight and Changeling exchanges it, the engine
    already restores both ``supply["Knights"]`` and pushes the variant back
    onto ``pile_order["Knights"]``. Summon must NOT double-restore — the
    pile and supply must look untouched, and the player gets a Changeling.
    """
    state = _new_state(["Knights", "Changeling"])
    player = state.players[0]
    player.cost_reduction = 1
    player.ai.should_exchange_changeling = lambda s, p, c: True

    starting_knights_supply = state.supply["Knights"]
    starting_changeling_supply = state.supply["Changeling"]
    starting_order_len = len(state.pile_order["Knights"])
    starting_top = state.pile_order["Knights"][-1]

    summon = get_event("Summon")
    summon.on_buy(state, player)

    # Knights pile unchanged (Changeling pushed the knight back).
    assert state.supply["Knights"] == starting_knights_supply
    assert len(state.pile_order["Knights"]) == starting_order_len
    assert state.pile_order["Knights"][-1] == starting_top
    # Changeling pile decreased by 1.
    assert state.supply["Changeling"] == starting_changeling_supply - 1
    # Player set aside a Changeling.
    assert len(player.summon_set_aside) == 1
    assert player.summon_set_aside[0].name == "Changeling"


def test_summon_start_play_fires_action_play_hooks():
    """When the Summoned card auto-plays at start of turn, the post-play
    hook chain (notably the Adventures tavern trigger "action_played")
    must fire so Reserve cards on the Tavern mat get a chance to react.

    Witness: Coin of the Realm on the Tavern mat grants +2 Actions when
    called after an Action play. With our default AI saying "yes" to the
    call, playing the Summoned Village should trigger Coin of the Realm.
    """
    state = _new_state(["Village", "Coin of the Realm"])
    player = state.players[0]
    coin = get_card("Coin of the Realm")
    player.tavern_mat.append(coin)
    player.ai.should_call_from_tavern = lambda s, p, c, trigger, *args: True

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1

    starting_actions = player.actions
    state.phase = "start"
    state.handle_start_phase()

    # Coin of the Realm should have been called: +2 Actions on top of
    # whatever Village's own +2 Actions already added.
    assert player.actions == starting_actions + 2 + 2
    # Coin of the Realm leaves the tavern mat when called.
    assert coin not in player.tavern_mat


def test_summon_skips_buried_split_pile_cards():
    """Wizards split pile (Student / Conjurer / Sorcerer / Lich): Conjurer
    is a $4 Action but is buried under Student. While Student has copies,
    ``may_be_bought`` returns False on Conjurer and Summon must NOT gain it.

    Setup: Student ($2 Action) on top of Wizards. Default AI prefers the
    higher-cost Action — without the filter, Conjurer ($4) wins; with the
    filter, Student ($2) is the only eligible card.
    """
    state = _new_state(["Student"])
    player = state.players[0]
    # Verify pre-conditions for the test premise.
    assert state.supply["Student"] > 0
    assert state.supply["Conjurer"] > 0
    assert get_card("Conjurer").may_be_bought(state) is False

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert len(player.summon_set_aside) == 1
    # Filter must exclude buried Conjurer; AI falls back to Student.
    assert player.summon_set_aside[0].name == "Student"
    assert state.supply["Conjurer"] == 4  # buried pile untouched


def test_summon_skips_traveller_and_reward_piles():
    """Page's Traveller chain (Treasure Hunter / Warrior / Hero / Champion)
    and Joust Rewards are added to ``state.supply`` via ``get_additional_piles``
    but are NOT Supply piles. Summon must filter them out — Treasure
    Hunter is a $3 Action that would otherwise be eligible.
    """
    state = _new_state(["Page", "Joust"])
    player = state.players[0]

    # Sanity: the leak surface is real — these names are in supply.
    assert "Treasure Hunter" in state.supply
    assert "Warrior" in state.supply
    assert "Coronet" in state.supply  # Joust Reward

    # Zero out the kingdom Action piles so a missing filter would force
    # Summon to pick a Traveller.
    for kingdom_name in ("Page", "Joust"):
        state.supply[kingdom_name] = 0

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert player.summon_set_aside == []
    # Non-Supply piles must be untouched.
    assert state.supply["Treasure Hunter"] == 5
    assert state.supply["Warrior"] == 5
    assert state.supply["Coronet"] == 5


def test_summon_skips_non_supply_piles():
    """Madman lives in ``state.supply`` (it's a non-Supply pile registered
    when Hermit is in the kingdom) but is not actually a Supply pile.
    Summon must NOT consider it as a candidate even though it's a $0 Action.
    """
    state = _new_state(["Hermit", "Smithy"])
    player = state.players[0]

    # Madman lives in state.supply (Hermit-game registers it directly) but
    # is NOT a Supply pile and Summon must not gain it.
    assert "Madman" in state.supply

    # Zero out every legitimate Action ≤ $4 in the Supply so that, if the
    # filter were missing, Summon would have no choice but to pick Madman.
    for name in list(state.supply.keys()):
        if name == "Madman":
            continue
        try:
            card = get_card(name)
        except Exception:
            continue
        if card.is_action and card.cost.coins <= 4:
            state.supply[name] = 0

    summon = get_event("Summon")
    summon.on_buy(state, player)
    assert player.summon_set_aside == []
    # And Madman supply is untouched.
    assert state.supply["Madman"] == 10


def test_summon_trader_replacement_on_knight_restores_pile_state():
    """If Trader replaces the Summoned Knight gain with a Silver, the
    Knights pile must be left untouched: pile_order keeps its top card and
    the Knights supply count is not decremented (since no Knight was
    actually gained from the pile).
    """
    state = _new_state(["Knights"])
    player = state.players[0]
    player.cost_reduction = 1  # makes Knights effectively $4
    player.hand = [get_card("Trader")]
    player.ai.should_reveal_trader = lambda s, p, original, to_deck=False: True

    starting_supply = state.supply["Knights"]
    starting_order_top = state.pile_order["Knights"][-1]
    starting_order_len = len(state.pile_order["Knights"])
    starting_silver_supply = state.supply["Silver"]

    summon = get_event("Summon")
    summon.on_buy(state, player)

    # Knights pile must be unchanged.
    assert state.supply["Knights"] == starting_supply
    assert len(state.pile_order["Knights"]) == starting_order_len
    assert state.pile_order["Knights"][-1] == starting_order_top
    # A Silver was gained instead. It went to discard via Trader; my
    # post-gain rerouting moves the Silver into summon_set_aside.
    assert state.supply["Silver"] == starting_silver_supply - 1
    assert len(player.summon_set_aside) == 1
    assert player.summon_set_aside[0].name == "Silver"


def test_summon_watchtower_trash_diverts_set_aside():
    """If Watchtower trashes the gained card, it must not be set aside."""
    state = _new_state(["Village"])
    player = state.players[0]
    player.hand = [get_card("Watchtower")]

    # Force Watchtower to always trash the gain.
    player.ai.choose_watchtower_reaction = lambda s, p, c: "trash"

    summon = get_event("Summon")
    starting_supply = state.supply["Village"]
    summon.on_buy(state, player)
    # Set-aside zone must be empty.
    assert player.summon_set_aside == []
    # The gained Village must be in the trash, not in the player's deck/discard.
    assert any(c.name == "Village" for c in state.trash)
    # Supply still decremented (the gain happened).
    assert state.supply["Village"] == starting_supply - 1
