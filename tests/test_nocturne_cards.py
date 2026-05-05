"""Tests for Nocturne kingdom cards (30 cards)."""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _PlayAllAI(DummyAI):
    def choose_action(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_buy(self, state, choices):
        for c in choices:
            if c is not None:
                return c
        return None

    def choose_card_to_trash(self, state, choices):
        for c in choices:
            if c.name == "Estate":
                return c
        for c in choices:
            if c.name == "Copper":
                return c
        return choices[0] if choices else None

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return choices[:count]

    def should_play_haunted_mirror_action_discard(self, state, player, actions):
        return actions[0] if actions else None


def _setup(ai=None, players=1):
    ais = [ai or _PlayAllAI() for _ in range(players)]
    state = GameState(players=[])
    state.log_callback = lambda *_: None
    state.players = [PlayerState(a) for a in ais]
    for p in state.players:
        p.initialize()
    state.supply = {
        "Copper": 30, "Silver": 20, "Gold": 10, "Curse": 10,
        "Estate": 10, "Duchy": 10, "Province": 8,
        "Will-o'-Wisp": 12, "Imp": 13, "Ghost": 6, "Bat": 10, "Wish": 12,
        "Vampire": 10,
        "Bard": 10, "Druid": 10, "Tracker": 10, "Pixie": 10,
        "Village": 10, "Smithy": 10, "Cellar": 10,
    }
    return state, state.players[0]


# ----- Kingdom card behaviors -----

def test_bard_grants_two_coins_and_a_boon():
    state, player = _setup()
    bard = get_card("Bard")
    player.hand = [bard]
    player.in_play = []
    player.actions = 1
    coins_before = player.coins
    player.hand.remove(bard)
    player.in_play.append(bard)
    bard.on_play(state)
    assert player.coins >= coins_before + 2  # Boon may add more


def test_blessed_village_on_gain_receives_boon():
    state, player = _setup()
    bv = get_card("Blessed Village")
    state.boons_deck = ["The Mountain's Gift"]
    silver_before = state.supply["Silver"]
    bv.on_gain(state, player)
    # Mountain's Gift gives a Silver
    assert state.supply["Silver"] == silver_before - 1


def test_cemetery_on_gain_trashes_up_to_four():
    state, player = _setup()
    cem = get_card("Cemetery")
    player.hand = [
        get_card("Estate"), get_card("Estate"), get_card("Copper"),
        get_card("Curse"), get_card("Silver"),
    ]
    cem.on_gain(state, player)
    # Silver should remain
    assert any(c.name == "Silver" for c in player.hand)
    # Estates / Curses / Coppers should be trashed
    trash_names = {c.name for c in state.trash}
    assert "Estate" in trash_names or "Curse" in trash_names


def test_changeling_trashes_self_and_gains_in_play_card():
    state, player = _setup()
    ch = get_card("Changeling")
    player.in_play = [ch, get_card("Village"), get_card("Smithy")]
    ch.play_effect(state)
    # Changeling went to trash
    assert ch in state.trash
    # Either Village or Smithy gained
    gained = {c.name for c in player.discard}
    assert gained & {"Village", "Smithy"}


def test_cobbler_duration_gains_card_to_hand_next_turn():
    state, player = _setup()
    cobbler = get_card("Cobbler")
    player.in_play = [cobbler]
    cobbler.play_effect(state)
    assert cobbler in player.duration
    # Next turn duration call
    cobbler.on_duration(state)
    # Should have gained a card up to $4 directly to hand
    assert any(c.cost.coins <= 4 for c in player.hand)


def test_conclave_plays_action_not_already_in_play():
    state, player = _setup()
    conclave = get_card("Conclave")
    village = get_card("Village")
    player.in_play = [conclave]
    player.hand = [village]
    player.actions = 0
    conclave.play_effect(state)
    # Village was played
    assert village in player.in_play
    # +1 Action because we played one
    assert player.actions >= 1


def test_cursed_village_draws_to_six_and_hexes():
    state, player = _setup()
    cv = get_card("Cursed Village")
    player.hand = []
    player.deck = [get_card("Copper") for _ in range(8)]
    player.actions = 1
    state.hex_deck = ["Greed"]
    state.hex_discard = []
    player.in_play.append(cv)
    cv.on_play(state)
    assert len(player.hand) >= 6
    # +2 Actions
    assert player.actions == 3


def test_den_of_sin_drawn_into_hand_on_gain():
    state, player = _setup()
    dos = get_card("Den of Sin")
    player.hand = []
    dos.on_gain(state, player)
    assert dos in player.hand


def test_devils_workshop_zero_gains_picks_card_up_to_four():
    state, player = _setup()
    dw = get_card("Devil's Workshop")
    player.cards_gained_this_turn_count = 0
    silver_before = state.supply.get("Silver", 0)
    dw.play_effect(state)
    # Should gain up to $4 — most expensive available
    # (Silver is $3, Duchy is $5, Smithy/Village are $4)
    assert any(c.cost.coins <= 4 for c in player.discard)


def test_devils_workshop_one_gain_yields_gold():
    state, player = _setup()
    dw = get_card("Devil's Workshop")
    player.cards_gained_this_turn_count = 1
    gold_before = state.supply["Gold"]
    dw.play_effect(state)
    assert state.supply["Gold"] == gold_before - 1


def test_devils_workshop_two_or_more_yields_imp():
    state, player = _setup()
    dw = get_card("Devil's Workshop")
    player.cards_gained_this_turn_count = 2
    imp_before = state.supply["Imp"]
    dw.play_effect(state)
    assert state.supply["Imp"] == imp_before - 1


def test_druid_uses_set_aside_boon():
    state, player = _setup()
    state.druid_boons = ["The Mountain's Gift", "The Sea's Gift", "The Field's Gift"]
    druid = get_card("Druid")
    silver_before = state.supply["Silver"]
    player.in_play.append(druid)
    druid.play_effect(state)
    # Default AI picks first → Mountain's Gift → gain Silver
    assert state.supply["Silver"] == silver_before - 1


def test_exorcist_trashes_then_gains_cheaper():
    state, player = _setup()
    ex = get_card("Exorcist")
    player.hand = [get_card("Smithy")]  # $4
    ex.play_effect(state)
    # Should have trashed Smithy, gained a cheaper Action
    assert any(c.name == "Smithy" for c in state.trash)


def test_faithful_hound_returns_to_hand_when_discarded():
    state, player = _setup()
    hound = get_card("Faithful Hound")
    player.discard.append(hound)
    # Trigger reaction
    hound.react_to_discard(state, player)
    # Hound was set aside
    assert hound not in player.discard
    assert hasattr(player, "hound_set_aside")
    assert hound in player.hound_set_aside


def test_fool_grants_three_boons_and_lost_in_woods():
    state, player = _setup()
    fool = get_card("Fool")
    state.boons_deck = ["The Sea's Gift", "The Sea's Gift", "The Mountain's Gift"]
    player.hand = []
    player.deck = [get_card("Copper"), get_card("Silver")]
    silver_before = state.supply["Silver"]
    player.in_play.append(fool)
    fool.play_effect(state)
    assert player.lost_in_the_woods
    # Mountain's Gift gave a silver
    assert state.supply["Silver"] == silver_before - 1


def test_ghost_town_to_hand_on_gain():
    state, player = _setup()
    gt = get_card("Ghost Town")
    gt.on_gain(state, player)
    assert gt in player.hand


def test_guardian_blocks_attacks_until_next_turn():
    state, player = _setup()
    guardian = get_card("Guardian")
    player.in_play = [guardian]
    guardian.play_effect(state)
    assert guardian in player.duration
    # Now an attack should be blocked
    assert state._player_blocks_attack(player) is True


def test_idol_odd_count_grants_boon_and_two_coins():
    state, player = _setup()
    idol = get_card("Idol")
    player.in_play = [idol]
    state.boons_deck = ["The Mountain's Gift"]
    coins_before = player.coins
    silver_before = state.supply["Silver"]
    idol.play_effect(state)
    assert player.coins == coins_before + 2
    assert state.supply["Silver"] == silver_before - 1


def test_idol_even_count_curses_others():
    state, player = _setup(players=2)
    other = state.players[1]
    other.hand = []
    idol1 = get_card("Idol")
    idol2 = get_card("Idol")
    player.in_play = [idol1, idol2]
    idol2.play_effect(state)
    assert any(c.name == "Curse" for c in other.discard)


def test_leprechaun_gains_gold_and_hex():
    state, player = _setup()
    state.hex_deck = ["Greed"]
    lep = get_card("Leprechaun")
    player.in_play = [lep]
    gold_before = state.supply["Gold"]
    lep.play_effect(state)
    assert state.supply["Gold"] == gold_before - 1


def test_monastery_trashes_per_card_gained():
    state, player = _setup()
    mon = get_card("Monastery")
    player.cards_gained_this_turn_count = 2
    player.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    mon.play_effect(state)
    # Two cards trashed, Silver kept
    assert len(state.trash) >= 2
    assert any(c.name == "Silver" for c in player.hand)


def test_necromancer_plays_action_from_trash():
    state, player = _setup()
    necro = get_card("Necromancer")
    village = get_card("Village")
    state.trash = [village]
    player.in_play = [necro]
    player.actions = 0
    necro.play_effect(state)
    # Village gives +2 Actions
    assert player.actions >= 2


def test_night_watchman_topdecks_keepers():
    state, player = _setup()
    nw = get_card("Night Watchman")
    player.deck = [get_card("Estate"), get_card("Silver"), get_card("Gold"), get_card("Curse"), get_card("Smithy")]
    player.in_play = [nw]
    nw.play_effect(state)
    # Estate and Curse get discarded, Silver/Gold/Smithy topdecked
    assert any(c.name in {"Estate", "Curse"} for c in player.discard)


def test_pixie_trashes_for_persistent_boon():
    state, player = _setup()
    pixie = get_card("Pixie")
    player.in_play = [pixie]
    state.boons_deck = ["The Field's Gift"]
    pixie.play_effect(state)
    # Pixie trashed
    assert pixie in state.trash
    # Field's Gift gave +1 Action and +$1
    assert player.coins >= 1


def test_pooka_trashes_treasure_for_four_cards():
    state, player = _setup()
    pooka = get_card("Pooka")
    player.in_play = [pooka]
    player.hand = [get_card("Copper")]
    player.deck = [get_card("Silver") for _ in range(5)]
    pooka.play_effect(state)
    assert any(c.name == "Copper" for c in state.trash)
    assert len(player.hand) >= 4


def test_raider_gives_three_coins_next_turn():
    state, player = _setup(players=2)
    raider = get_card("Raider")
    player.in_play = [raider]
    raider.play_effect(state)
    assert raider in player.duration
    coins_before = player.coins
    raider.on_duration(state)
    assert player.coins == coins_before + 3


def test_sacred_grove_three_coins_buy_and_boon():
    state, player = _setup()
    sg = get_card("Sacred Grove")
    state.boons_deck = ["The Mountain's Gift"]
    silver_before = state.supply["Silver"]
    player.hand = [sg]
    player.hand.remove(sg)
    player.in_play.append(sg)
    sg.on_play(state)
    assert player.coins >= 3
    assert player.buys >= 2
    assert state.supply["Silver"] == silver_before - 1


def test_secret_cave_with_three_discards_grants_three_next_turn():
    state, player = _setup()

    class CaveAI(_PlayAllAI):
        def choose_secret_cave_discards(self, state, player):
            return list(player.hand[:3])

    state.players[0].ai = CaveAI()
    cave = get_card("Secret Cave")
    player.in_play = [cave]
    player.hand = [get_card("Copper"), get_card("Copper"), get_card("Copper")]
    cave.play_effect(state)
    assert cave in player.duration
    coins_before = player.coins
    cave.on_duration(state)
    assert player.coins == coins_before + 3


def test_shepherd_discards_victories_for_two_each():
    state, player = _setup()
    shep = get_card("Shepherd")
    player.in_play = [shep]
    player.hand = [get_card("Estate"), get_card("Estate")]
    player.deck = [get_card("Silver") for _ in range(5)]
    shep.play_effect(state)
    # Discarded 2 Estates → +4 cards drawn
    assert len(player.hand) >= 4


def test_tormentor_with_only_self_in_play_gains_imp():
    state, player = _setup()
    torm = get_card("Tormentor")
    player.in_play = [torm]
    imp_before = state.supply["Imp"]
    torm.play_effect(state)
    assert state.supply["Imp"] == imp_before - 1


def test_tracker_grants_action_coin_and_boon():
    state, player = _setup()
    tracker = get_card("Tracker")
    state.boons_deck = ["The Mountain's Gift"]
    silver_before = state.supply["Silver"]
    player.hand = [tracker]
    player.actions = 1
    player.hand.remove(tracker)
    player.in_play.append(tracker)
    tracker.on_play(state)
    assert player.actions == 2
    assert player.coins >= 1
    assert state.supply["Silver"] == silver_before - 1


def test_vampire_attacks_gains_card_and_swaps_to_bat():
    state, player = _setup(players=2)
    vamp = get_card("Vampire")
    state.hex_deck = ["Greed"]
    state.supply["Vampire"] = 9  # Just played
    player.in_play = [vamp]
    bat_before = state.supply["Bat"]
    vamp.play_effect(state)
    # Vampire returned to pile
    assert state.supply["Vampire"] == 10
    # Gained a Bat
    assert state.supply["Bat"] == bat_before - 1


def test_werewolf_action_phase_grants_three_cards():
    state, player = _setup()
    werewolf = get_card("Werewolf")
    state.phase = "action"
    player.in_play = [werewolf]
    player.deck = [get_card("Silver") for _ in range(5)]
    werewolf.play_effect(state)
    assert len(player.hand) >= 3


def test_werewolf_night_phase_attacks():
    state, player = _setup(players=2)
    werewolf = get_card("Werewolf")
    state.phase = "night"
    state.hex_deck = ["Greed"]
    state.hex_discard = []
    player.in_play = [werewolf]
    werewolf.play_effect(state)
    # Other player got a hex (Greed → topdecked Copper)
    other = state.players[1]
    assert any(c.name == "Copper" for c in other.deck) or len(state.hex_discard) > 0


# ----- PR #191 review fixes -----


def test_bat_is_typed_as_night_only():
    """Bat must be a Night card, not Action/Shadow, so it cannot be played in
    the Action phase (or from the deck via Shadow handling)."""
    bat = get_card("Bat")
    assert bat.is_night
    assert not bat.is_action
    assert not bat.is_shadow


def test_raider_attack_works_against_small_hand():
    """Raider must force a discard whenever the target has a matching card,
    regardless of hand size; previous code immunized hands of <5 cards."""

    state, player = _setup(players=2)
    raider = get_card("Raider")
    other = state.players[1]
    # Make sure Raider's in-play set will match a card in the target's small
    # hand. Use Copper (always in the supply) as the matched card.
    player.in_play = [raider, get_card("Copper")]
    other.hand = [get_card("Copper"), get_card("Estate")]
    raider.play_effect(state)
    # The matching Copper should have been discarded.
    assert any(c.name == "Copper" for c in other.discard)
    assert not any(c.name == "Copper" for c in other.hand)


def test_druid_persistent_boon_attaches_to_player():
    """Druid granting a persistent Boon (Field's Gift) must track it on the
    player so its next-turn effect survives — but on the Druid-specific
    list, not on ``active_boons`` (which gets discarded each turn)."""

    state, player = _setup()
    state.druid_boons = ["The Field's Gift", "The Sea's Gift", "The Mountain's Gift"]
    druid = get_card("Druid")
    player.in_play.append(druid)
    actions_before = player.actions
    druid.play_effect(state)
    # The Field's Gift gave +1 Action and +$1 immediately.
    assert player.actions >= actions_before + 1
    # Tracked on the Druid-specific list so the start-of-turn cleanup
    # applies the bonus without sending it to the boon discard pile.
    assert hasattr(player, "druid_active_boons")
    assert "The Field's Gift" in player.druid_active_boons
    # Must NOT leak into the regular active_boons list, otherwise the
    # next-turn cleanup would discard it.
    assert "The Field's Gift" not in getattr(player, "active_boons", [])


def test_necromancer_zombies_start_in_trash():
    """Necromancer's three Zombies must start in the trash, not in the
    supply, so Necromancer has legal targets from turn 1."""

    from dominion.cards.nocturne.necromancer import Necromancer

    state, player = _setup()
    state.trash = []
    state._setup_nocturne_extras([Necromancer()])
    trash_names = {c.name for c in state.trash}
    assert "Zombie Apprentice" in trash_names
    assert "Zombie Mason" in trash_names
    assert "Zombie Spy" in trash_names
    # And they should NOT be in the supply.
    assert "Zombie Apprentice" not in state.supply
    assert "Zombie Mason" not in state.supply
    assert "Zombie Spy" not in state.supply


def test_changeling_exchange_on_gain_when_ai_opts_in():
    """Gaining a $3+ card with Changeling in supply must offer the exchange
    (when the AI opts in, the gain becomes a Changeling)."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    state.supply["Smithy"] = 10
    smithy_before = state.supply["Smithy"]
    changeling_before = state.supply["Changeling"]
    smithy = get_card("Smithy")  # cost $4
    state.supply["Smithy"] -= 1
    state.gain_card(player, smithy)
    # Exchanged: Smithy returned, Changeling came out, Changeling now in
    # the player's discard.
    assert state.supply["Smithy"] == smithy_before
    assert state.supply["Changeling"] == changeling_before - 1
    assert any(c.name == "Changeling" for c in player.discard)
    assert not any(c.name == "Smithy" for c in player.discard)


def test_changeling_exchange_skipped_for_cheap_gains():
    """Gaining a card costing <$3 must not trigger Changeling exchange."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    changeling_before = state.supply["Changeling"]
    estate = get_card("Estate")  # cost $2
    state.supply["Estate"] -= 1
    state.gain_card(player, estate)
    assert state.supply["Changeling"] == changeling_before
    assert any(c.name == "Estate" for c in player.discard)


def test_changeling_exchange_skipped_when_gaining_changeling():
    """Gaining a Changeling itself must not trigger an exchange loop."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    changeling_before = state.supply["Changeling"]
    state.supply["Changeling"] -= 1
    state.gain_card(player, get_card("Changeling"))
    # Net: one Changeling came out of the pile and ended up in discard.
    assert state.supply["Changeling"] == changeling_before - 1
    assert sum(1 for c in player.discard if c.name == "Changeling") == 1


def test_changeling_exchange_preserves_topdeck_position():
    """When a gained card is topdecked (e.g. via Royal Seal) and then
    exchanged for a Changeling, the Changeling must replace the gained
    card in the SAME deck slot (the top), not get appended to the
    bottom."""

    class TopdeckExchangeAI(_PlayAllAI):
        def should_topdeck_with_royal_seal(self, state, player, gained_card):
            return True

        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=TopdeckExchangeAI())
    state.supply["Changeling"] = 10
    state.supply["Smithy"] = 10

    # Pre-existing deck contents (these are below the topdecked gain).
    estate_a = get_card("Estate")
    estate_b = get_card("Estate")
    player.deck = [estate_a, estate_b]

    # Royal Seal in play so the gain gets topdecked.
    player.in_play.append(get_card("Royal Seal"))

    smithy = get_card("Smithy")  # cost $4
    state.supply["Smithy"] -= 1
    state.gain_card(player, smithy)

    # Changeling must sit at the top of the deck (last element), where
    # Royal Seal placed Smithy before the exchange replaced it.
    assert player.deck, "deck should not be empty after exchange"
    assert player.deck[-1].name == "Changeling", (
        f"top-of-deck should be Changeling, got {[c.name for c in player.deck]}"
    )
    # And the original deck order below it must be untouched.
    assert player.deck[0] is estate_a
    assert player.deck[1] is estate_b
    # Smithy returned to the supply, no Smithy/Changeling leaked into discard.
    assert not any(c.name == "Smithy" for c in player.discard)
    assert not any(c.name == "Changeling" for c in player.discard)


def test_changeling_uses_effective_cost_at_gain_peddler_full_cost():
    """At full printed cost ($8), Peddler is well above Changeling's $3
    threshold, so the exchange MUST be offered."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    state.supply["Peddler"] = 10
    # No Actions in play -> Peddler's effective cost == printed cost ($8).
    player.in_play = []
    changeling_before = state.supply["Changeling"]
    peddler_before = state.supply["Peddler"]

    peddler = get_card("Peddler")  # printed cost $8
    state.supply["Peddler"] -= 1
    state.gain_card(player, peddler)

    # Exchange happened: Peddler returned, a Changeling was taken.
    assert state.supply["Peddler"] == peddler_before
    assert state.supply["Changeling"] == changeling_before - 1
    assert any(c.name == "Changeling" for c in player.discard)
    assert not any(c.name == "Peddler" for c in player.discard)


def test_changeling_uses_effective_cost_at_gain_peddler_reduced_below_three():
    """Bridge in play reduces every card's cost by $1. With 2 Bridges +
    actions in play that drop Peddler to $0–$2, gaining a Peddler must
    NOT trigger the Changeling exchange because the effective cost is
    below $3."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    state.supply["Peddler"] = 10

    # Stack three Bridges in play -> player.cost_reduction = 3, so
    # every card gets -$3. Combined with 2 actions in play
    # (Peddler -$4 from cost_modifier), Peddler effective cost is
    # max(0, 8 - 4 - 3) = 1, which is below $3.
    player.cost_reduction = 3
    # Two Action cards in play to trigger Peddler's cost_modifier.
    player.in_play = [get_card("Village"), get_card("Smithy")]

    # Sanity: confirm get_card_cost agrees the effective cost is < 3.
    peddler_template = get_card("Peddler")
    assert state.get_card_cost(player, peddler_template) < 3

    changeling_before = state.supply["Changeling"]
    peddler_before = state.supply["Peddler"]

    peddler = get_card("Peddler")
    state.supply["Peddler"] -= 1
    state.gain_card(player, peddler)

    # No exchange: Changeling pile untouched, Peddler stays in discard.
    assert state.supply["Changeling"] == changeling_before
    assert state.supply["Peddler"] == peddler_before - 1
    assert any(c.name == "Peddler" for c in player.discard)
    assert not any(c.name == "Changeling" for c in player.discard)


def test_changeling_exchange_skipped_for_non_supply_card():
    """If a card without a Supply pile (e.g. Necromancer's Zombies, which
    live in `nocturne_trash_piles` and start in the trash) somehow reaches
    a player's hand/discard/deck via gain_card, Changeling must NOT
    exchange it — there's no pile to return the original to. The card
    must remain wherever gain_card put it; nothing must vanish from the
    game and no Changeling must be granted."""

    class ExchangeAI(_PlayAllAI):
        def should_exchange_changeling(self, state, player, gained_card):
            return True

    state, player = _setup(ai=ExchangeAI())
    state.supply["Changeling"] = 10
    # Zombie is intentionally NOT in state.supply — it lives in
    # nocturne_trash_piles and is normally only ever in state.trash.
    assert "Zombie Apprentice" not in state.supply

    changeling_before = state.supply["Changeling"]
    zombie = get_card("Zombie Apprentice")  # cost $3, qualifies on cost
    state.gain_card(player, zombie)

    # The Zombie must still be in the player's discard (where gain_card
    # placed it) — it must NOT have vanished from the game.
    assert any(c is zombie for c in player.discard), (
        "Non-supply gained card vanished from the game during attempted "
        "Changeling exchange"
    )
    # No Changeling came out of the pile, no Changeling in discard.
    assert state.supply["Changeling"] == changeling_before
    assert not any(c.name == "Changeling" for c in player.discard)


def test_druid_boons_persist_across_multiple_turns():
    """Druid's three set-aside Boons must NEVER be sent to the boons
    discard pile — they remain set aside for the entire game and continue
    delivering their next-turn bonuses every turn until something else
    happens."""

    state, player = _setup()
    state.druid_boons = ["The Field's Gift", "The Forest's Gift", "The River's Gift"]
    boons_discard_before = list(state.boons_discard)

    druid = get_card("Druid")
    player.in_play.append(druid)

    # Receive Field's Gift via Druid (immediate +1 Action +$1).
    actions_before = player.actions
    coins_before = player.coins
    druid.play_effect(state)
    assert player.actions == actions_before + 1
    assert player.coins == coins_before + 1
    assert player.druid_active_boons == ["The Field's Gift"]

    # Simulate several start-of-turn cleanups. The Druid Boon should
    # fire its bonus EACH start-of-turn (via the cleanup hook) but never
    # appear in the boons discard, and the Druid set-aside list must
    # stay intact.
    for turn_idx in range(3):
        actions_before = player.actions
        coins_before = player.coins
        state.handle_start_phase()
        # Field's Gift fires +1 Action +$1.
        assert player.actions >= actions_before + 1, (
            f"turn {turn_idx}: Druid Field's Gift should give +1 Action"
        )
        assert player.coins >= coins_before + 1, (
            f"turn {turn_idx}: Druid Field's Gift should give +$1"
        )
        # The boon must not have been discarded.
        assert "The Field's Gift" not in state.boons_discard, (
            f"turn {turn_idx}: Druid Boon leaked into boons discard"
        )
        # The 3 set-aside Boons remain set aside.
        assert set(state.druid_boons) == {
            "The Field's Gift",
            "The Forest's Gift",
            "The River's Gift",
        }
        # Re-attach for next iteration: the player's druid_active_boons
        # was cleared by handle_start_phase. Re-play Druid to re-receive
        # Field's Gift so the next iteration can verify continued effect.
        druid.play_effect(state)

    # Final invariant: nothing Druid-related ended up in boons_discard.
    new_in_discard = [b for b in state.boons_discard if b not in boons_discard_before]
    for b in new_in_discard:
        assert b not in {"The Field's Gift", "The Forest's Gift", "The River's Gift"}


def test_druid_river_gift_grants_cleanup_draw_without_discarding():
    """Druid receiving River's Gift grants the +1-card cleanup draw, and
    the Boon stays set aside (not in active_boons, not in boons discard)."""

    state, player = _setup()
    state.druid_boons = ["The River's Gift", "The Sea's Gift", "The Mountain's Gift"]

    # Player needs cards in deck to draw (cleanup draws the new hand).
    player.deck = [get_card("Copper") for _ in range(10)]
    player.hand = []
    player.discard = []
    player.in_play.append(get_card("Druid"))

    druid = get_card("Druid")
    druid.play_effect(state)
    # River's Gift was chosen.
    assert player.druid_active_boons == ["The River's Gift"]
    # Persistent Boon must not appear on the regular active_boons list.
    assert "The River's Gift" not in player.active_boons

    # Cleanup the turn: River's Gift adds +1 to the cleanup draw, so the
    # newly drawn hand should be 5 + 1 = 6 cards.
    state.handle_cleanup_phase()
    assert len(player.hand) == 6, (
        f"River's Gift cleanup draw should produce a 6-card hand, got {len(player.hand)}"
    )
    # Boon stayed set aside, not discarded.
    assert "The River's Gift" not in state.boons_discard
    assert "The River's Gift" in state.druid_boons
