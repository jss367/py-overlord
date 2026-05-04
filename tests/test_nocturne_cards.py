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
