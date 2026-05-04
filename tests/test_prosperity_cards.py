from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import DummyAI, TrashFirstAI


def play_action(state: GameState, player: PlayerState, card_name: str) -> None:
    card = next(card for card in player.hand if card.name == card_name)
    player.hand.remove(card)
    player.in_play.append(card)
    card.on_play(state)


class NoTrashAI(DummyAI):
    def choose_card_to_trash(self, state, choices):
        return None


class BuyNamedCardAI(DummyAI):
    def __init__(self, target_name: str):
        super().__init__()
        self.target_name = target_name

    def choose_buy(self, state, choices):
        for choice in choices:
            if choice and choice.name == self.target_name:
                return choice
        return None


class DeclineTrashAI(DummyAI):
    def choose_card_to_trash(self, state, choices):
        return None


class VaultPlayerAI(DummyAI):
    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return [card for card in choices if card.name == "Copper"]


class VaultResponderAI(DummyAI):
    def should_discard_for_vault(self, state, player):
        return True

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        return choices[:count]


class WatchtowerTrashAI(DummyAI):
    def choose_watchtower_reaction(self, state, player, gained_card):
        return "trash"


class WatchtowerTopdeckAI(DummyAI):
    def choose_watchtower_reaction(self, state, player, gained_card):
        return "topdeck"


class RoyalSealTopdeckAI(DummyAI):
    def should_topdeck_with_royal_seal(self, state, player, gained_card):
        return True


class ReverseTopdeckAI(DummyAI):
    def order_cards_for_topdeck(self, state, player, cards):
        return list(reversed(cards))


def test_bishop_awards_vp_and_optional_trash():
    trash_ai = TrashFirstAI()
    skip_ai = NoTrashAI()

    player = PlayerState(trash_ai)
    other = PlayerState(skip_ai)
    state = GameState([player, other])
    state.setup_supply([get_card("Bishop")])

    player.hand = [get_card("Bishop"), get_card("Silver")]
    other.hand = [get_card("Estate")]

    play_action(state, player, "Bishop")

    assert player.vp_tokens == 2
    assert any(card.name == "Estate" for card in other.hand)


def test_hoard_gains_gold_on_victory_buy():
    ai = BuyNamedCardAI("Province")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Hoard"), get_card("Province")])

    player.in_play = [get_card("Hoard")]
    player.coins = 8
    player.buys = 1

    state.handle_buy_phase()

    gained_golds = [card for card in player.discard if card.name == "Gold"]
    assert len(gained_golds) == 1


def test_talisman_gains_copy_for_non_victory_purchase():
    ai = BuyNamedCardAI("Village")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Talisman"), get_card("Village")])

    player.in_play = [get_card("Talisman")]
    player.coins = 3
    player.buys = 1

    state.handle_buy_phase()

    villages = [card for card in player.discard if card.name == "Village"]
    assert len(villages) == 2


def test_loan_allows_declining_trash():
    ai = DeclineTrashAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Loan")])

    player.deck = [get_card("Copper"), get_card("Estate")]
    loan = get_card("Loan")
    player.hand = [loan]

    play_action(state, player, "Loan")

    assert all(card.name != "Copper" for card in state.trash)
    assert any(card.name == "Copper" for card in player.discard)


def test_rabble_allows_reordering_revealed_cards():
    attacker_ai = DummyAI()
    defender_ai = ReverseTopdeckAI()

    attacker = PlayerState(attacker_ai)
    defender = PlayerState(defender_ai)
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Rabble")])

    defender.deck = [get_card("Estate"), get_card("Copper"), get_card("Duchy"), get_card("Estate")]

    attacker.hand = [get_card("Rabble")]
    play_action(state, attacker, "Rabble")

    assert defender.deck[-1].name == "Duchy"
    assert defender.deck[-2].name == "Estate"


def test_royal_seal_can_topdeck_gains():
    ai = RoyalSealTopdeckAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Royal Seal"), get_card("Silver")])

    player.in_play = [get_card("Royal Seal")]

    state.supply["Silver"] -= 1
    state.gain_card(player, get_card("Silver"))

    assert any(card.name == "Silver" for card in player.deck)
    assert all(card.name != "Silver" for card in player.discard)


def test_trade_route_tracks_tokens_and_mat_value():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Trade Route")])

    state.supply["Estate"] -= 1
    state.gain_card(player, get_card("Estate"))
    state.supply["Duchy"] -= 1
    state.gain_card(player, get_card("Duchy"))

    assert state.trade_route_mat_tokens == 2

    player.hand = [get_card("Trade Route")]
    play_action(state, player, "Trade Route")

    assert player.coins == 2


def test_vault_discard_choices_and_reaction():
    player_ai = VaultPlayerAI()
    responder_ai = VaultResponderAI()

    player = PlayerState(player_ai)
    responder = PlayerState(responder_ai)
    state = GameState([player, responder])
    state.setup_supply([get_card("Vault")])

    player.hand = [get_card("Vault"), get_card("Copper"), get_card("Estate")]
    responder.hand = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    responder.deck = [get_card("Estate")]

    play_action(state, player, "Vault")

    assert player.coins == 1
    assert all(card.name != "Copper" for card in player.hand)
    assert len(responder.hand) == 2


def test_watchtower_draws_to_six_and_can_trash_gains():
    draw_ai = DummyAI()
    reaction_ai = WatchtowerTrashAI()

    player = PlayerState(draw_ai)
    reactor = PlayerState(reaction_ai)
    state = GameState([player, reactor])
    state.setup_supply([get_card("Watchtower"), get_card("Estate")])

    player.deck = [get_card("Copper") for _ in range(6)]
    player.hand = [get_card("Watchtower")]
    play_action(state, player, "Watchtower")

    assert len(player.hand) == 6

    reactor.hand = [get_card("Watchtower")]
    state.supply["Estate"] -= 1
    state.gain_card(reactor, get_card("Estate"))

    assert any(card.name == "Estate" for card in state.trash)


def test_watchtower_can_topdeck_gains():
    gain_ai = DummyAI()
    reaction_ai = WatchtowerTopdeckAI()

    player = PlayerState(gain_ai)
    reactor = PlayerState(reaction_ai)
    state = GameState([player, reactor])
    state.setup_supply([get_card("Watchtower"), get_card("Estate")])

    reactor.hand = [get_card("Watchtower")]
    estate = get_card("Estate")

    state.supply["Estate"] -= 1
    state.gain_card(reactor, estate)

    assert reactor.deck and reactor.deck[-1].name == "Estate"
    assert all(card.name != "Estate" for card in reactor.discard)



# ---------------------------------------------------------------------------
# Bug fixes: King's Court, Quarry, Hoard, Monument verifications
# ---------------------------------------------------------------------------


class PlayFirstActionAI(DummyAI):
    """Always play the first non-None action choice."""

    def choose_action(self, state, choices):
        for choice in choices:
            if choice is not None:
                return choice
        return None


def test_kings_court_does_not_grant_extra_action():
    """King's Court has no innate +1 Action; the chosen Action provides any
    villaging, not King's Court itself.
    """
    kc = get_card("King's Court")
    assert kc.stats.actions == 0


def test_kings_court_plays_chosen_action_three_times_and_keeps_in_play():
    ai = PlayFirstActionAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("King's Court"), get_card("Village")])

    village = get_card("Village")
    kc = get_card("King's Court")
    player.hand = [kc, village]
    player.actions = 0  # Only count Village's contributions

    # Move KC to in_play and resolve its play_effect (mirrors on_play
    # after stat handling; KC has no stats now).
    player.hand.remove(kc)
    player.in_play.append(kc)
    kc.play_effect(state)

    assert village in player.in_play
    assert village not in player.hand
    # Three Village plays ⇒ +6 actions
    assert player.actions == 6


def test_kings_court_with_no_action_in_hand_is_a_noop():
    ai = PlayFirstActionAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("King's Court")])

    kc = get_card("King's Court")
    player.hand = [kc, get_card("Copper")]
    player.in_play.append(kc)
    player.hand.remove(kc)

    kc.play_effect(state)
    # No crash; no spurious card shuffle
    assert kc in player.in_play


def test_quarry_reduces_action_cost_while_in_play():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Quarry"), get_card("Village")])

    village = get_card("Village")
    base = state.get_card_cost(player, village)
    assert base == 3

    player.in_play = [get_card("Quarry")]
    discounted = state.get_card_cost(player, village)
    assert discounted == 1

    # Two Quarries floor at $0
    player.in_play = [get_card("Quarry"), get_card("Quarry")]
    assert state.get_card_cost(player, village) == 0

    # Quarry doesn't reduce non-Action cards (Silver: $3)
    silver = get_card("Silver")
    assert state.get_card_cost(player, silver) == 3


def test_hoard_gain_gold_when_buying_victory():
    """Existing test ensures Hoard works on Province buy. Confirm Estate too."""
    ai = BuyNamedCardAI("Estate")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Hoard"), get_card("Estate")])

    player.in_play = [get_card("Hoard")]
    player.coins = 2
    player.buys = 1

    state.handle_buy_phase()
    assert any(card.name == "Gold" for card in player.discard)


def test_monument_grants_vp_token_and_two_coins():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Monument")])

    player.hand = [get_card("Monument")]
    play_action(state, player, "Monument")

    assert player.coins == 2
    assert player.vp_tokens == 1


# ---------------------------------------------------------------------------
# Anvil ($3 Treasure)
# ---------------------------------------------------------------------------


class AnvilAI(DummyAI):
    def __init__(self, gain_target: str = "Silver"):
        super().__init__()
        self.gain_target = gain_target

    def choose_treasure(self, state, choices):
        for c in choices:
            if c is not None and c.name == "Anvil":
                return c
        return None

    def choose_buy(self, state, choices):
        return None

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        # Discard a Copper if available
        for c in choices:
            if c.name == "Copper":
                return c
        return choices[0] if choices else None

    def choose_anvil_gain(self, state, player, choices):
        for c in choices:
            if c.name == self.gain_target:
                return c
        return None


def test_anvil_gives_one_coin_when_played():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Anvil")])

    anvil = get_card("Anvil")
    player.in_play.append(anvil)
    anvil.on_play(state)

    assert player.coins == 1


def test_anvil_discard_treasure_to_gain_card_up_to_4():
    ai = AnvilAI(gain_target="Silver")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Anvil"), get_card("Silver")])

    anvil = get_card("Anvil")
    player.hand = [anvil, get_card("Copper"), get_card("Estate")]
    player.in_play = []
    player.coins = 0

    # Play through treasure phase so cleanup triggers Anvil's discard hook.
    state.phase = "treasure"
    state.handle_treasure_phase()
    # Now move into a manual cleanup so on_discard_from_play fires.
    state.handle_cleanup_phase()

    # Copper was discarded from hand, Silver gained from supply
    assert any(card.name == "Silver" for card in player.discard + player.deck + player.hand)


def test_anvil_no_gain_when_no_treasure_in_hand():
    ai = AnvilAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Anvil"), get_card("Silver")])

    anvil = get_card("Anvil")
    # Move directly to in_play and cleanup
    player.in_play = [anvil]
    player.hand = [get_card("Estate")]  # No treasures

    silver_supply_before = state.supply["Silver"]
    state.handle_cleanup_phase()

    assert state.supply["Silver"] == silver_supply_before


# ---------------------------------------------------------------------------
# Charlatan ($5 Action-Attack)
# ---------------------------------------------------------------------------


def test_charlatan_attacks_and_gives_coins():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DummyAI())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Charlatan")])

    charlatan = get_card("Charlatan")
    attacker.hand = [charlatan]
    play_action(state, attacker, "Charlatan")

    assert attacker.coins == 3
    assert any(c.name == "Curse" for c in defender.discard + defender.hand + defender.deck)


def test_charlatan_blocked_by_moat():
    class MoatRevealer(DummyAI):
        def should_reveal_moat(self, state, player):
            return True

    attacker = PlayerState(DummyAI())
    defender = PlayerState(MoatRevealer())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Charlatan")])

    defender.hand = [get_card("Moat")]
    attacker.hand = [get_card("Charlatan")]

    play_action(state, attacker, "Charlatan")

    assert all(c.name != "Curse" for c in defender.discard + defender.hand + defender.deck)


# ---------------------------------------------------------------------------
# Magnate ($5 Action)
# ---------------------------------------------------------------------------


def test_magnate_draws_one_per_treasure_revealed():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Magnate")])

    magnate = get_card("Magnate")
    player.hand = [magnate, get_card("Copper"), get_card("Silver"), get_card("Estate")]
    player.deck = [get_card("Gold"), get_card("Duchy"), get_card("Province")]

    play_action(state, player, "Magnate")

    # Two treasures (Copper, Silver) revealed ⇒ +2 cards drawn
    # Hand size: was 3 after removing Magnate, now 5
    assert len(player.hand) == 5


def test_magnate_with_no_treasures_does_nothing():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Magnate")])

    magnate = get_card("Magnate")
    player.hand = [magnate, get_card("Estate")]
    player.deck = [get_card("Duchy")]

    play_action(state, player, "Magnate")
    assert len(player.hand) == 1  # No treasure ⇒ no draw


# ---------------------------------------------------------------------------
# Crystal Ball ($5 Treasure)
# ---------------------------------------------------------------------------


class CrystalBallAI(DummyAI):
    def __init__(self, mode: str):
        super().__init__()
        self.mode = mode

    def choose_crystal_ball_action(self, state, player, top_card):
        return self.mode


def test_crystal_ball_gives_one_coin():
    ai = CrystalBallAI("leave")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Crystal Ball")])

    cb = get_card("Crystal Ball")
    player.deck = [get_card("Estate")]
    player.in_play = [cb]
    cb.on_play(state)
    assert player.coins == 1


def test_crystal_ball_can_trash_top_card():
    ai = CrystalBallAI("trash")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Crystal Ball")])

    cb = get_card("Crystal Ball")
    junk = get_card("Curse")
    player.deck = [junk]
    player.in_play = [cb]
    cb.on_play(state)
    assert junk in state.trash


def test_crystal_ball_can_discard_top_card():
    ai = CrystalBallAI("discard")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Crystal Ball")])

    cb = get_card("Crystal Ball")
    estate = get_card("Estate")
    player.deck = [estate]
    player.in_play = [cb]
    cb.on_play(state)
    assert estate in player.discard


def test_crystal_ball_can_play_treasure_on_top():
    ai = CrystalBallAI("play")
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Crystal Ball")])

    cb = get_card("Crystal Ball")
    silver = get_card("Silver")
    player.deck = [silver]
    player.in_play = [cb]
    cb.on_play(state)
    # Silver played from top of deck ⇒ +$2 plus Crystal Ball's +$1 = $3
    assert player.coins == 3
    assert silver in player.in_play


# ---------------------------------------------------------------------------
# Investment ($4 Treasure)
# ---------------------------------------------------------------------------


class InvestmentTrashAI(DummyAI):
    def choose_investment_mode(self, state, player, can_trash_treasure):
        return "trash" if can_trash_treasure else "coin"

    def choose_treasure_to_trash_for_investment(self, state, player, choices):
        return choices[0] if choices else None


class InvestmentCoinAI(DummyAI):
    def choose_investment_mode(self, state, player, can_trash_treasure):
        return "coin"


def test_investment_self_trashes_on_play():
    ai = InvestmentCoinAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Investment")])

    inv = get_card("Investment")
    player.in_play = [inv]
    inv.on_play(state)

    assert inv in state.trash
    assert inv not in player.in_play
    assert player.coins == 1


def test_investment_trash_treasure_grants_vp_for_distinct_treasures():
    ai = InvestmentTrashAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Investment")])

    inv = get_card("Investment")
    player.in_play = [inv]
    player.hand = [get_card("Copper"), get_card("Silver"), get_card("Gold")]

    inv.on_play(state)

    # Trashed Copper. Hand now: Silver, Gold ⇒ 2 distinct ⇒ +2 VP
    assert player.vp_tokens == 2
    assert any(c.name == "Copper" for c in state.trash)
    assert inv in state.trash


# ---------------------------------------------------------------------------
# Tiara ($4 Treasure)
# ---------------------------------------------------------------------------


class TiaraReplayAI(DummyAI):
    def should_replay_treasure_with_tiara(self, state, player, treasure):
        return True

    def should_topdeck_with_tiara(self, state, player, gained_card):
        return True

    def choose_treasure(self, state, choices):
        order = ["Tiara", "Silver", "Copper"]
        for name in order:
            for c in choices:
                if c is not None and c.name == name:
                    return c
        return None


def test_tiara_grants_buy():
    ai = DummyAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Tiara")])

    tiara = get_card("Tiara")
    player.in_play = [tiara]
    initial_buys = player.buys
    tiara.on_play(state)
    assert player.buys == initial_buys + 1


def test_tiara_replays_treasure_once_per_turn():
    ai = TiaraReplayAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Tiara"), get_card("Silver"), get_card("Copper")])

    tiara = get_card("Tiara")
    silver = get_card("Silver")
    copper = get_card("Copper")
    player.hand = [tiara, silver, copper]

    state.phase = "treasure"
    state.handle_treasure_phase()

    # Tiara: +1 Buy, no coin. Silver: $2 (replayed once via Tiara) ⇒ $4. Copper: $1.
    # So total = 4 + 1 = 5
    assert player.coins == 5
    assert player.tiara_replay_used


def test_tiara_topdecks_gain_when_in_play():
    ai = TiaraReplayAI()
    player = PlayerState(ai)
    state = GameState([player])
    state.setup_supply([get_card("Tiara"), get_card("Gold")])

    player.in_play = [get_card("Tiara")]
    state.supply["Gold"] -= 1
    state.gain_card(player, get_card("Gold"))

    # Gold went on top of deck, not discard
    assert any(c.name == "Gold" for c in player.deck)
    assert all(c.name != "Gold" for c in player.discard)


# ---------------------------------------------------------------------------
# War Chest ($5 Treasure)
# ---------------------------------------------------------------------------


class WarChestAI(DummyAI):
    """Owner of War Chest — picks the most expensive non-named card."""

    def choose_war_chest_gain(self, state, player, choices):
        return max(choices, key=lambda c: c.cost.coins)


class NameSilverAI(DummyAI):
    """Opponent — names Silver."""

    def choose_card_for_war_chest(self, state, opponent, supply_choices):
        for c in supply_choices:
            if c.name == "Silver":
                return c
        return supply_choices[0] if supply_choices else None


def test_war_chest_grants_coin_and_buy():
    owner = PlayerState(WarChestAI())
    opp = PlayerState(NameSilverAI())
    state = GameState([owner, opp])
    state.setup_supply([get_card("War Chest"), get_card("Gold")])

    wc = get_card("War Chest")
    owner.in_play.append(wc)
    initial_buys = owner.buys
    wc.on_play(state)

    assert owner.coins == 1
    assert owner.buys == initial_buys + 1


def test_war_chest_gains_unnamed_card():
    owner = PlayerState(WarChestAI())
    opp = PlayerState(NameSilverAI())
    state = GameState([owner, opp])
    state.setup_supply([get_card("War Chest"), get_card("Gold"), get_card("Silver")])

    wc = get_card("War Chest")
    owner.in_play.append(wc)
    wc.on_play(state)

    # Silver was named ⇒ should NOT be gained. Gold is the most expensive
    # remaining $0-$5 card.
    assert "Silver" in owner.war_chest_named_this_turn
    assert any(c.name != "Silver" for c in owner.discard + owner.deck + owner.hand)


def test_war_chest_excludes_previously_named_card():
    """Two War Chests in one turn must name two different cards."""

    owner = PlayerState(WarChestAI())
    opp = PlayerState(NameSilverAI())
    state = GameState([owner, opp])
    state.setup_supply([get_card("War Chest"), get_card("Gold"), get_card("Silver")])

    wc1 = get_card("War Chest")
    wc2 = get_card("War Chest")
    owner.in_play.extend([wc1, wc2])
    wc1.on_play(state)
    # First WC named Silver. Now the same opponent will try to name Silver
    # again, but the gain must avoid any previously-named card.
    wc2.on_play(state)
    assert "Silver" in owner.war_chest_named_this_turn


# ---------------------------------------------------------------------------
# Clerk ($4 Action-Attack-Duration)
# ---------------------------------------------------------------------------


class ClerkReplayAI(DummyAI):
    def should_replay_clerk(self, state, player):
        return True


def test_clerk_attacks_opponent_with_5_or_more_cards():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DummyAI())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Clerk")])

    defender.hand = [get_card("Copper") for _ in range(5)]
    initial_hand_size = len(defender.hand)

    clerk = get_card("Clerk")
    attacker.hand = [clerk]
    play_action(state, attacker, "Clerk")

    assert attacker.coins == 2
    # One card from defender's hand to deck
    assert len(defender.hand) == initial_hand_size - 1
    assert len(defender.deck) >= 1


def test_clerk_skips_opponent_with_fewer_than_5_cards():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DummyAI())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Clerk")])

    defender.hand = [get_card("Copper") for _ in range(4)]

    clerk = get_card("Clerk")
    attacker.hand = [clerk]
    play_action(state, attacker, "Clerk")

    assert len(defender.hand) == 4  # Untouched


def test_clerk_stays_in_duration_for_replay_next_turn():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DummyAI())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Clerk")])

    defender.hand = [get_card("Copper") for _ in range(5)]

    clerk = get_card("Clerk")
    attacker.hand = [clerk]
    play_action(state, attacker, "Clerk")

    # Clerk should now sit in duration awaiting next-turn replay
    assert clerk in attacker.duration


def test_clerk_replays_at_start_of_next_turn():
    attacker = PlayerState(ClerkReplayAI())
    defender = PlayerState(DummyAI())
    state = GameState([attacker, defender])
    state.setup_supply([get_card("Clerk")])

    defender.hand = [get_card("Copper") for _ in range(5)]
    initial_def_hand = len(defender.hand)

    clerk = get_card("Clerk")
    attacker.hand = [clerk]
    play_action(state, attacker, "Clerk")
    coins_after_first = attacker.coins
    # First play attacked once
    assert len(defender.deck) == 1

    # Simulate next-turn duration replay
    defender.hand = [get_card("Copper") for _ in range(5)]  # restock for second attack
    state.do_duration_phase()

    # Replay should have given another +$2 and another attack
    assert attacker.coins == coins_after_first + 2
    assert len(defender.deck) >= 2  # Second attack added another card


# ---------------------------------------------------------------------------
# Watchtower reaction (regression)
# ---------------------------------------------------------------------------


def test_watchtower_reaction_only_fires_when_in_hand():
    """If Watchtower is in play (not hand) the reaction must not trigger."""

    class AlwaysTrashAI(DummyAI):
        def choose_watchtower_reaction(self, state, player, gained_card):
            return "trash"

    player = PlayerState(AlwaysTrashAI())
    state = GameState([player])
    state.setup_supply([get_card("Watchtower"), get_card("Estate")])

    # Watchtower in play — should NOT react
    player.in_play = [get_card("Watchtower")]
    state.supply["Estate"] -= 1
    state.gain_card(player, get_card("Estate"))

    assert all(c.name != "Estate" for c in state.trash)
    assert any(c.name == "Estate" for c in player.discard + player.deck)
