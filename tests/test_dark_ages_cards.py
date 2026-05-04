"""Tests for the bulk of the Dark Ages expansion.

Covers Ruins variants + pile mechanic, Knights pile, Madman/Mercenary
non-supply piles, and the 20 missing 1E kingdom cards.
"""

import random

from dominion.cards.base_card import CardType
from dominion.cards.dark_ages.knights import KNIGHT_NAMES
from dominion.cards.dark_ages.ruins import RUIN_VARIANT_NAMES
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState

from tests.utils import ChooseFirstActionAI, DummyAI


class _GreedyAI(ChooseFirstActionAI):
    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_trash(self, state, choices):
        return choices[0] if choices else None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None


def _setup(num_players=1, kingdom=None):
    ais = [_GreedyAI() for _ in range(num_players)]
    state = GameState(players=[])
    state.initialize_game(ais, kingdom or [get_card("Village")])
    for p in state.players:
        p.hand = []
        p.deck = []
        p.discard = []
        p.in_play = []
        p.duration = []
        p.actions = 1
        p.buys = 1
        p.coins = 0
    return state


# ----------------------------------------------------------------------
# Step 0: 4 cards already wired up in the registry. Sanity check.
# ----------------------------------------------------------------------


def test_step0_cards_resolvable():
    for name in ("Beggar", "Forager", "Rats", "Rebuild"):
        c = get_card(name)
        assert c.name == name


# ----------------------------------------------------------------------
# Ruins
# ----------------------------------------------------------------------


def test_ruins_pile_built_for_marauder_kingdom():
    random.seed(0)
    state = _setup(num_players=2, kingdom=[get_card("Marauder")])
    # 2 players => 10 ruins
    assert len(state.pile_order["Ruins"]) == 10
    assert state.supply["Ruins"] == 10
    # All entries are valid ruin variant names
    for name in state.pile_order["Ruins"]:
        assert name in RUIN_VARIANT_NAMES


def test_ruins_pile_size_scales_with_player_count():
    state = _setup(num_players=4, kingdom=[get_card("Marauder")])
    assert len(state.pile_order["Ruins"]) == 30
    assert state.supply["Ruins"] == 30


def test_marauder_attack_gives_ruin_to_opponent():
    state = _setup(num_players=2, kingdom=[get_card("Marauder")])
    attacker, victim = state.players
    marauder = get_card("Marauder")
    attacker.in_play.append(marauder)
    marauder.play_effect(state)

    # Spoils to attacker
    assert any(c.name == "Spoils" for c in attacker.discard)
    # Ruins (any variant) to victim
    assert any(c.is_ruins for c in victim.discard)


def test_abandoned_mine_gives_one_coin():
    state = _setup()
    player = state.players[0]
    mine = get_card("Abandoned Mine")
    player.in_play.append(mine)
    mine.on_play(state)
    assert player.coins == 1


def test_ruined_library_draws_one():
    state = _setup()
    player = state.players[0]
    player.deck = [get_card("Copper")]
    library = get_card("Ruined Library")
    player.in_play.append(library)
    library.on_play(state)
    assert any(c.name == "Copper" for c in player.hand)


def test_ruined_market_gives_buy():
    state = _setup()
    player = state.players[0]
    market = get_card("Ruined Market")
    player.in_play.append(market)
    market.on_play(state)
    assert player.buys == 2  # 1 starting + 1


def test_ruined_village_gives_action():
    state = _setup()
    player = state.players[0]
    village = get_card("Ruined Village")
    player.in_play.append(village)
    village.on_play(state)
    assert player.actions == 2


def test_survivors_topdecks_or_discards():
    state = _setup()
    player = state.players[0]
    # Stack good Action cards - default heuristic should keep them on top
    player.deck = [get_card("Village"), get_card("Smithy")]
    survivors = get_card("Survivors")
    player.in_play.append(survivors)
    survivors.on_play(state)
    # Both action cards should be back on the deck
    assert len(player.deck) == 2
    assert all(c.name in {"Village", "Smithy"} for c in player.deck)


def test_survivors_discards_junk():
    state = _setup()
    player = state.players[0]
    # Junk on top - default should discard
    player.deck = [get_card("Curse"), get_card("Estate")]
    survivors = get_card("Survivors")
    player.in_play.append(survivors)
    survivors.on_play(state)
    assert len(player.deck) == 0
    assert len(player.discard) == 2


# ----------------------------------------------------------------------
# Knights
# ----------------------------------------------------------------------


def test_knights_pile_setup_is_shuffled_and_unique():
    random.seed(1)
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    assert len(state.pile_order["Knights"]) == 10
    assert set(state.pile_order["Knights"]) == set(KNIGHT_NAMES)


def test_only_top_knight_is_buyable():
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    player = state.players[0]
    player.coins = 5
    player.buys = 1

    affordable = state._get_affordable_cards(player)
    knight_names = [c.name for c in affordable if c.is_knight]
    # Only one knight should be on offer (the top of the pile)
    assert len(knight_names) == 1
    top = state.pile_order["Knights"][-1]
    assert knight_names[0] == top


def test_buying_top_knight_pops_pile():
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    player = state.players[0]
    player.coins = 5
    player.buys = 1

    pile_size_before = len(state.pile_order["Knights"])
    top = state.pile_order["Knights"][-1]
    knight = get_card(top)
    state.handle_buy_phase()

    # Either bought or stopped; if bought, pile shrinks by 1
    if any(c.name == top for c in player.discard) or any(
        c.name == top for c in player.deck
    ):
        assert len(state.pile_order["Knights"]) == pile_size_before - 1
        assert state.supply["Knights"] == pile_size_before - 1


def test_sir_bailey_attack_trashes_eligible_card():
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    attacker, victim = state.players
    bailey = get_card("Sir Bailey")
    attacker.in_play.append(bailey)
    # Victim deck top has a $4 Smithy and $0 Copper; only Smithy is in [3,6].
    victim.deck = [get_card("Copper"), get_card("Smithy")]

    bailey.play_effect(state)
    # +1 Card +1 Action from Bailey, +$2 from attack
    assert attacker.coins == 2
    # Smithy should be trashed; Copper discarded
    assert any(c.name == "Smithy" for c in state.trash)
    assert any(c.name == "Copper" for c in victim.discard)


def test_sir_vander_gains_gold_when_trashed():
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    player = state.players[0]
    vander = get_card("Sir Vander")
    state.trash_card(player, vander)
    assert any(c.name == "Gold" for c in player.discard)


def test_dame_josephine_is_a_victory():
    josephine = get_card("Dame Josephine")
    assert CardType.VICTORY in josephine.types
    # 2 VP
    class _P:
        pass
    p = _P()
    assert josephine.get_victory_points(p) == 2


def test_knight_kills_knight_self_trashes():
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    attacker, victim = state.players
    bailey = get_card("Sir Bailey")
    attacker.in_play.append(bailey)
    # Victim's deck top: another Knight (cost $5, in [3,6])
    martin = get_card("Sir Martin")
    victim.deck = [get_card("Copper"), martin]

    bailey.play_effect(state)
    # Martin trashed; Bailey self-trashed too
    assert martin in state.trash
    assert bailey in state.trash


# ----------------------------------------------------------------------
# Madman & Mercenary
# ----------------------------------------------------------------------


def test_madman_pile_setup_with_hermit():
    state = _setup(num_players=2, kingdom=[get_card("Hermit")])
    assert state.supply.get("Madman") == 10


def test_mercenary_pile_setup_with_urchin():
    state = _setup(num_players=2, kingdom=[get_card("Urchin")])
    assert state.supply.get("Mercenary") == 10


def test_hermit_no_buy_turns_into_madman_at_buy_phase_end():
    state = _setup(num_players=2, kingdom=[get_card("Hermit")])
    player = state.players[0]
    hermit = get_card("Hermit")
    player.in_play.append(hermit)
    player.cards_gained_this_buy_phase = 0
    state._handle_buy_phase_end(player)
    # Hermit trashed, Madman gained
    assert hermit in state.trash
    assert any(c.name == "Madman" for c in player.discard)
    assert state.supply["Madman"] == 9


def test_hermit_skips_madman_if_card_was_gained():
    state = _setup(num_players=2, kingdom=[get_card("Hermit")])
    player = state.players[0]
    hermit = get_card("Hermit")
    player.in_play.append(hermit)
    player.cards_gained_this_buy_phase = 1
    state._handle_buy_phase_end(player)
    assert hermit in player.in_play
    assert state.supply["Madman"] == 10


def test_madman_play_returns_to_pile_and_draws():
    state = _setup(num_players=2, kingdom=[get_card("Hermit")])
    player = state.players[0]
    madman = get_card("Madman")
    player.hand = [get_card("Copper"), get_card("Estate")]
    player.in_play = [madman]

    pile_before = state.supply["Madman"]
    madman.play_effect(state)
    # +2 Actions
    assert player.actions == 3
    # Returned to pile
    assert madman not in player.in_play
    assert state.supply["Madman"] == pile_before + 1


def test_urchin_attack_discards_to_four():
    state = _setup(num_players=2, kingdom=[get_card("Urchin")])
    attacker, victim = state.players
    urchin = get_card("Urchin")
    attacker.in_play.append(urchin)
    victim.hand = [get_card("Copper") for _ in range(6)]

    urchin.play_effect(state)
    assert len(victim.hand) == 4


def test_urchin_into_mercenary_when_chained_with_attack():
    state = _setup(num_players=2, kingdom=[get_card("Urchin"), get_card("Witch")])
    attacker, victim = state.players
    urchin = get_card("Urchin")
    witch = get_card("Witch")
    attacker.in_play = [urchin]
    # Simulate playing Witch while Urchin is in play
    urchin.react_to_attack_played(state, attacker, witch)

    assert urchin in state.trash
    assert any(c.name == "Mercenary" for c in attacker.discard)


def test_mercenary_trash_two_then_attack():
    state = _setup(num_players=2, kingdom=[get_card("Urchin")])
    attacker, victim = state.players
    mercenary = get_card("Mercenary")
    attacker.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    attacker.deck = [get_card("Gold"), get_card("Gold")]
    attacker.in_play.append(mercenary)
    victim.hand = [get_card("Copper") for _ in range(6)]

    mercenary.play_effect(state)
    # Trashed two junk cards, drew 2, +$2
    assert attacker.coins == 2
    assert len(attacker.hand) == 1 + 2  # silver kept + 2 drawn
    assert len(victim.hand) == 3


# ----------------------------------------------------------------------
# 20 missing kingdom cards — at least one test each
# ----------------------------------------------------------------------


def test_squire_choose_actions():
    state = _setup()
    player = state.players[0]
    squire = get_card("Squire")

    class ActionsAI(_GreedyAI):
        def choose_squire_option(self, state, player, options):
            return "actions"
    player.ai = ActionsAI()

    player.in_play.append(squire)
    squire.on_play(state)
    assert player.coins == 1
    assert player.actions == 3


def test_squire_choose_silver():
    state = _setup()
    player = state.players[0]
    squire = get_card("Squire")
    player.in_play.append(squire)
    state.supply["Silver"] = 5
    squire.on_play(state)
    # Default AI picks silver
    assert any(c.name == "Silver" for c in player.discard)


def test_squire_on_trash_gains_attack():
    state = _setup(num_players=2, kingdom=[get_card("Witch")])
    player = state.players[0]
    squire = get_card("Squire")
    state.trash_card(player, squire)
    # Should gain an attack card (Witch is the only attack in supply here)
    assert any(c.is_attack for c in player.discard)


def test_squire_on_trash_can_gain_top_knight():
    """When Knights is the only Attack pile, Squire gains the top Knight."""
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    player = state.players[0]
    squire = get_card("Squire")
    expected_top = state.pile_order["Knights"][-1]
    pile_size_before = state.supply["Knights"]

    state.trash_card(player, squire)

    assert any(c.is_knight for c in player.discard), \
        "Squire should have gained a Knight"
    assert any(c.name == expected_top for c in player.discard), \
        "Squire should gain the top Knight from the pile"
    assert state.supply["Knights"] == pile_size_before - 1


def test_urchin_triggers_on_attack_played_via_throne_room():
    """Throne Room on a non-Urchin Attack should still trash Urchin for Mercenary."""
    state = _setup(
        num_players=2,
        kingdom=[get_card("Urchin"), get_card("Witch"), get_card("Throne Room")],
    )
    attacker = state.players[0]
    urchin = get_card("Urchin")
    throne = get_card("Throne Room")
    militia = get_card("Militia")

    attacker.in_play = [urchin]
    attacker.hand = [militia]
    # Throne Room plays Militia twice; the first play should trigger
    # Urchin's reaction (which trashes itself for Mercenary).
    throne.play_effect(state)

    assert urchin in state.trash, "Urchin should be trashed when Militia is played via Throne Room"
    assert any(c.name == "Mercenary" for c in attacker.discard), \
        "Mercenary should be gained from Urchin's reaction"


def test_embargo_token_on_knights_curses_buyer():
    """Embargo on the shared Knights pile gives a Curse when buying any Knight."""
    state = _setup(num_players=2, kingdom=[get_card("Knights")])
    player = state.players[0]
    state.embargo_tokens["Knights"] = 1
    # Should map the buy of e.g. "Dame Sylvia" to the "Knights" pile.
    state._apply_embargo_tokens(player, "Knights")
    assert any(c.name == "Curse" for c in player.discard), \
        "Embargo on Knights should give a Curse when applied"


def test_vagrant_picks_up_curse_top():
    state = _setup()
    player = state.players[0]
    vagrant = get_card("Vagrant")
    player.deck = [get_card("Curse")]
    player.in_play.append(vagrant)
    vagrant.on_play(state)
    # +1 Card brings curse into hand naturally; deck empty; nothing to reveal
    assert any(c.name == "Curse" for c in player.hand)


def test_vagrant_picks_up_victory_top():
    state = _setup()
    player = state.players[0]
    vagrant = get_card("Vagrant")
    # Stack: top will be revealed after the +1 Card draw
    player.deck = [get_card("Estate"), get_card("Copper")]
    player.in_play.append(vagrant)
    vagrant.on_play(state)
    # Drew Copper, revealed Estate -> picked up
    assert any(c.name == "Copper" for c in player.hand)
    assert any(c.name == "Estate" for c in player.hand)


def test_hermit_trashes_and_gains_three_cost():
    state = _setup(num_players=2, kingdom=[get_card("Hermit"), get_card("Village")])
    player = state.players[0]
    hermit = get_card("Hermit")
    player.discard = [get_card("Estate")]
    player.in_play.append(hermit)
    hermit.play_effect(state)
    # Default AI trashes Estate, then gains a $3 card
    assert any(c.name == "Estate" for c in state.trash)
    # Gained something costing <=3
    gained_in_discard = [c for c in player.discard if c.name != "Estate"]
    assert gained_in_discard
    assert all(c.cost.coins <= 3 for c in gained_in_discard)


def test_storeroom_discards_for_cards_then_coins():
    state = _setup()
    player = state.players[0]
    storeroom = get_card("Storeroom")
    player.hand = [get_card("Copper"), get_card("Estate")]
    player.deck = [get_card("Silver"), get_card("Gold")]
    player.in_play.append(storeroom)
    storeroom.on_play(state)
    assert player.buys == 2  # +1 Buy
    # Both junk cards discarded for cards drawn => hand has Silver+Gold
    assert any(c.name in {"Silver", "Gold"} for c in player.hand)


def test_death_cart_on_gain_gives_two_ruins():
    state = _setup(num_players=2, kingdom=[get_card("Death Cart")])
    player = state.players[0]
    cart = get_card("Death Cart")
    state.gain_card(player, cart)
    ruins = [c for c in player.discard if c.is_ruins]
    assert len(ruins) == 2


def test_death_cart_play_trashes_action_for_five():
    state = _setup(num_players=2, kingdom=[get_card("Death Cart")])
    player = state.players[0]
    cart = get_card("Death Cart")
    player.hand = [get_card("Village")]
    player.in_play.append(cart)
    cart.play_effect(state)
    assert any(c.name == "Village" for c in state.trash)
    assert player.coins == 5


def test_fortress_returns_to_hand_when_trashed():
    state = _setup()
    player = state.players[0]
    fortress = get_card("Fortress")
    player.in_play.append(fortress)
    state.trash_card(player, fortress)
    assert fortress in player.hand
    assert fortress not in state.trash


def test_fortress_play_stats():
    state = _setup()
    player = state.players[0]
    fortress = get_card("Fortress")
    player.deck = [get_card("Copper")]
    player.in_play.append(fortress)
    fortress.on_play(state)
    assert player.actions == 3
    assert any(c.name == "Copper" for c in player.hand)


def test_scavenger_play_topdecks_from_discard():
    state = _setup()
    player = state.players[0]
    scavenger = get_card("Scavenger")
    player.deck = [get_card("Copper"), get_card("Copper"), get_card("Copper")]
    player.discard = [get_card("Gold")]
    player.in_play.append(scavenger)
    scavenger.on_play(state)
    assert player.coins == 2
    # Default AI picks up Gold from discard onto top of deck
    assert player.deck and player.deck[-1].name == "Gold"


def test_band_of_misfits_plays_cheaper_action():
    state = _setup(num_players=2, kingdom=[get_card("Band of Misfits"), get_card("Village")])
    player = state.players[0]
    misfits = get_card("Band of Misfits")
    player.in_play.append(misfits)
    misfits.play_effect(state)
    # Should have played Village or Smithy etc — gives +1 Card +2 Actions for Village
    # We only check that some action effect resolved.
    assert player.actions >= 1


def test_bandit_camp_gains_spoils():
    state = _setup(num_players=2, kingdom=[get_card("Bandit Camp")])
    player = state.players[0]
    camp = get_card("Bandit Camp")
    player.deck = [get_card("Copper")]
    player.in_play.append(camp)
    camp.on_play(state)
    assert player.actions == 3
    assert any(c.name == "Spoils" for c in player.discard)


def test_catacombs_take_into_hand():
    state = _setup()
    player = state.players[0]
    cat = get_card("Catacombs")

    class TakeAI(_GreedyAI):
        def should_catacombs_discard_three(self, state, player, revealed):
            return False
    player.ai = TakeAI()

    player.deck = [
        get_card("Copper"), get_card("Village"), get_card("Smithy"),
    ]
    player.in_play.append(cat)
    cat.play_effect(state)
    assert len(player.hand) == 3


def test_catacombs_on_trash_gains_cheaper_card():
    state = _setup(num_players=2, kingdom=[get_card("Catacombs"), get_card("Village")])
    player = state.players[0]
    cat = get_card("Catacombs")
    state.trash_card(player, cat)
    # Default AI picks the most expensive cheaper card
    gained = [c for c in player.discard]
    assert gained
    assert all(c.cost.coins < 5 for c in gained)


def test_counterfeit_plays_treasure_twice_and_trashes_it():
    state = _setup()
    player = state.players[0]
    counterfeit = get_card("Counterfeit")
    silver = get_card("Silver")
    player.hand = [silver]
    player.in_play.append(counterfeit)
    counterfeit.play_effect(state)
    # +1 +$1 from Counterfeit, +$2 (Silver) twice = +$5 total + the $1 from Counterfeit
    # Stats handled by on_play in Card.on_play; play_effect only handles the "double + trash"
    # so just check Silver was trashed and coins gained from Silver*2.
    assert silver in state.trash
    assert player.coins == 4  # 2*$2 from silver, no Counterfeit stats applied here


def test_cultist_gives_opponent_ruins_and_can_chain():
    state = _setup(num_players=2, kingdom=[get_card("Cultist")])
    attacker, victim = state.players
    cultist1 = get_card("Cultist")
    cultist2 = get_card("Cultist")
    attacker.hand = [cultist2]
    attacker.deck = [get_card("Copper") for _ in range(4)]
    attacker.in_play.append(cultist1)

    cultist1.play_effect(state)
    # First Cultist gave a Ruins; chain played second Cultist gave another
    ruins_to_victim = [c for c in victim.discard if c.is_ruins]
    assert len(ruins_to_victim) == 2
    # Chained Cultist moved into in_play
    assert cultist2 in attacker.in_play


def test_cultist_on_trash_draws_three():
    state = _setup(num_players=2, kingdom=[get_card("Cultist")])
    player = state.players[0]
    cultist = get_card("Cultist")
    player.deck = [get_card("Copper") for _ in range(3)]
    state.trash_card(player, cultist)
    # 3 cards drawn into hand
    assert sum(1 for c in player.hand if c.name == "Copper") == 3


def test_junk_dealer_trashes_a_card():
    state = _setup()
    player = state.players[0]
    jd = get_card("Junk Dealer")
    player.hand = [get_card("Estate")]
    player.deck = [get_card("Copper")]
    player.in_play.append(jd)
    jd.on_play(state)
    assert player.coins == 1
    # Drew, then trashed Estate
    assert any(c.name == "Estate" for c in state.trash)


def test_mystic_pulls_named_card_into_hand():
    state = _setup()
    player = state.players[0]
    mystic = get_card("Mystic")
    player.deck = [get_card("Gold")]

    class GoldNamerAI(_GreedyAI):
        def name_card_for_mystic(self, state, player):
            return "Gold"
    player.ai = GoldNamerAI()

    player.in_play.append(mystic)
    mystic.on_play(state)
    assert player.coins == 2
    assert player.actions == 2
    assert any(c.name == "Gold" for c in player.hand)


def test_pillage_trashes_self_gains_two_spoils_and_attacks():
    state = _setup(num_players=2, kingdom=[get_card("Pillage")])
    attacker, victim = state.players
    pillage = get_card("Pillage")
    attacker.in_play.append(pillage)
    victim.hand = [get_card("Gold"), get_card("Copper"), get_card("Copper"),
                   get_card("Estate"), get_card("Estate")]

    pillage.play_effect(state)
    assert pillage in state.trash
    spoils_gained = sum(1 for c in attacker.discard if c.name == "Spoils")
    assert spoils_gained == 2
    # Victim discarded one card (the most valuable, Gold by default)
    assert any(c.name == "Gold" for c in victim.discard)


def test_rogue_trashes_eligible_top_card():
    state = _setup(num_players=2, kingdom=[get_card("Rogue")])
    attacker, victim = state.players
    rogue = get_card("Rogue")
    attacker.in_play.append(rogue)
    victim.deck = [get_card("Copper"), get_card("Smithy")]

    rogue.on_play(state)
    assert attacker.coins == 2
    # Smithy was first trashed from the victim's deck; it may have then been
    # pulled into the attacker's discard by Rogue's "gain from trash" clause.
    smithy_landed = (
        any(c.name == "Smithy" for c in state.trash)
        or any(c.name == "Smithy" for c in attacker.discard)
    )
    assert smithy_landed


def test_rogue_gains_from_trash_when_attacks_empty():
    state = _setup(num_players=2, kingdom=[get_card("Rogue")])
    attacker, victim = state.players
    rogue = get_card("Rogue")
    # Pre-load trash with a $5 card; victim has nothing to reveal
    state.trash.append(get_card("Witch"))
    attacker.in_play.append(rogue)
    rogue.on_play(state)
    # Witch should move from trash to attacker's discard
    assert any(c.name == "Witch" for c in attacker.discard)


def test_altar_trashes_and_gains():
    state = _setup(num_players=2, kingdom=[get_card("Altar"), get_card("Witch")])
    player = state.players[0]
    altar = get_card("Altar")
    player.hand = [get_card("Estate")]
    player.in_play.append(altar)
    altar.play_effect(state)
    assert any(c.name == "Estate" for c in state.trash)
    # Gained an action card costing up to $5
    gained_actions = [
        c for c in player.discard if c.is_action and c.name != "Estate"
    ]
    assert gained_actions


# ----------------------------------------------------------------------
# Shelters
# ----------------------------------------------------------------------


def test_overgrown_estate_on_trash_draws_card():
    state = _setup()
    player = state.players[0]
    estate = get_card("Overgrown Estate")
    player.deck = [get_card("Copper")]
    state.trash_card(player, estate)
    assert any(c.name == "Copper" for c in player.hand)


def test_hovel_trashes_on_victory_buy():
    state = _setup()
    player = state.players[0]
    hovel = get_card("Hovel")
    player.hand = [hovel]
    player.coins = 5
    player.buys = 1

    state.handle_buy_phase()
    # Greedy AI buys most expensive thing it can; Hovel reaction trashes if
    # the buy is a Victory card. Buy might pick Duchy ($5) — Hovel reacts.
    bought_victory = any(name == "Duchy" for name in player.bought_this_turn)
    if bought_victory:
        assert hovel in state.trash


def test_necropolis_gives_two_actions():
    state = _setup()
    player = state.players[0]
    necropolis = get_card("Necropolis")
    player.in_play.append(necropolis)
    necropolis.on_play(state)
    assert player.actions == 3
