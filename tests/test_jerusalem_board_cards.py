"""Rules regressions found by the Jerusalem board card audit.

Kingdom: Goons, Sea Hag, Governor, Ambassador, Minion, Old Witch,
Scrying Pool, Fortress, Ill-Gotten Gains, Bridge Troll.
"""

from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


BOARD = [
    "Goons", "Sea Hag", "Governor", "Ambassador", "Minion",
    "Old Witch", "Scrying Pool", "Fortress", "Ill-Gotten Gains", "Bridge Troll",
]


class _PickAI(ChooseFirstActionAI):
    """Test AI whose gain/trash/mode choices can be scripted by name."""

    def __init__(self, wants=(), governor="cards", ambassador_return=None):
        super().__init__()
        self.wants = list(wants)
        self.governor = governor
        self.ambassador_return = ambassador_return

    def _pick(self, choices):
        for name in self.wants:
            for card in choices:
                if card is not None and card.name == name:
                    return card
        return None

    def choose_buy(self, state, choices):
        return self._pick(choices)

    def choose_card_to_trash(self, state, choices):
        return self._pick(choices)

    def choose_governor_option(self, state, player, options):
        return self.governor

    def choose_card_to_ambassador(self, state, player, choices):
        return self._pick(choices)

    def choose_ambassador_return_count(self, state, player, revealed, maximum):
        if self.ambassador_return is None:
            return super().choose_ambassador_return_count(
                state, player, revealed, maximum
            )
        return self.ambassador_return


def _setup(ais=None, kingdom=BOARD):
    ais = ais or [_PickAI() for _ in range(2)]
    state = GameState(players=[])
    state.initialize_game(ais, [get_card(name) for name in kingdom])
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


# ------------------------------------------------------- Ill-Gotten Gains


def test_ill_gotten_gains_grants_no_extra_buy():
    """"$1. When you play this, you may gain a Copper to your hand." No +Buy."""
    igg = get_card("Ill-Gotten Gains")
    assert igg.stats.buys == 0
    assert igg.stats.coins == 1


def test_ill_gotten_gains_curses_opponents_on_gain():
    state = _setup()
    player, victim = state.players
    state.supply["Ill-Gotten Gains"] -= 1
    state.gain_card(player, get_card("Ill-Gotten Gains"))
    assert sum(c.name == "Curse" for c in victim.discard) == 1


# ------------------------------------------------------------- Governor


def test_governor_upgrade_is_an_exact_cost_gain():
    """Governor gains a card costing *exactly* $2 more, not "up to" $2 more."""
    trasher = _PickAI(wants=["Estate", "Fortress", "Copper"], governor="upgrade")
    other = _PickAI(wants=[])
    state = _setup([trasher, other])
    player = state.players[0]
    player.hand = [get_card("Estate")]

    get_card("Governor").play_effect(state)

    gained = [c.name for c in player.discard]
    assert gained == ["Fortress"], gained  # Estate $2 -> exactly $4
    assert [c.name for c in state.trash] == ["Estate"]


def test_governor_upgrade_gains_nothing_when_no_exact_cost_card_exists():
    """Trashing a $9 card with no $11 pile in the Supply gains nothing."""
    trasher = _PickAI(wants=["Province"], governor="upgrade")
    state = _setup([trasher, _PickAI(wants=[])])
    player = state.players[0]
    player.hand = [get_card("Province")]

    get_card("Governor").play_effect(state)

    assert [c.name for c in state.trash] == ["Province"]
    assert player.discard == []


def test_governor_opponents_upgrade_by_exactly_one_coin():
    """Each other player "may trash a card and gain one costing exactly $1 more"."""
    trasher = _PickAI(wants=["Copper", "Minion"], governor="upgrade")
    victim = _PickAI(wants=["Estate", "Fortress", "Ambassador"])
    state = _setup([trasher, victim])
    state.players[0].hand = [get_card("Copper")]
    state.players[1].hand = [get_card("Estate")]

    get_card("Governor").play_effect(state)

    # The opponent trashed an Estate ($2), so only $3 piles are reachable:
    # the $4 Fortress they asked for first is out of range, and the "up to"
    # reading would have let them take it.
    assert [c.name for c in state.players[1].discard] == ["Ambassador"]
    assert sorted(c.name for c in state.trash) == ["Copper", "Estate"]


def test_governor_opponents_may_decline_to_trash():
    trasher = _PickAI(wants=["Estate"], governor="upgrade")
    decliner = _PickAI(wants=[])
    state = _setup([trasher, decliner])
    state.players[0].hand = [get_card("Estate")]
    state.players[1].hand = [get_card("Copper")]

    get_card("Governor").play_effect(state)

    assert [c.name for c in state.trash] == ["Estate"]
    assert [c.name for c in state.players[1].hand] == ["Copper"]


def test_governor_gold_option_gives_opponents_silver():
    state = _setup([_PickAI(governor="gold"), _PickAI()])
    player, victim = state.players
    get_card("Governor").play_effect(state)
    assert [c.name for c in player.discard] == ["Gold"]
    assert [c.name for c in victim.discard] == ["Silver"]


# ------------------------------------------------------------ Ambassador


def test_ambassador_return_count_is_a_strategy_decision():
    """"Return up to 2 copies": the count is chosen, not hardcoded by card name."""
    keeper = _PickAI(wants=["Silver"], ambassador_return=2)
    state = _setup([keeper, _PickAI()])
    player, victim = state.players
    player.hand = [get_card("Silver"), get_card("Silver")]
    before = state.supply["Silver"]

    get_card("Ambassador").play_effect(state)

    assert player.hand == []
    assert [c.name for c in victim.discard] == ["Silver"]
    # Two returned, one handed to the opponent.
    assert state.supply["Silver"] == before + 1


def test_ambassador_can_return_zero_copies():
    """Returning nothing still hands each opponent a copy."""
    giver = _PickAI(wants=["Curse"], ambassador_return=0)
    state = _setup([giver, _PickAI()])
    player, victim = state.players
    player.hand = [get_card("Curse")]
    before = state.supply["Curse"]

    get_card("Ambassador").play_effect(state)

    assert [c.name for c in player.hand] == ["Curse"]
    assert [c.name for c in victim.discard] == ["Curse"]
    assert state.supply["Curse"] == before - 1


def test_ambassador_default_policy_sheds_both_copies_of_junk():
    state = _setup()
    player, victim = state.players
    player.hand = [get_card("Estate"), get_card("Estate")]
    before = state.supply["Estate"]

    get_card("Ambassador").play_effect(state)

    assert player.hand == []
    assert state.supply["Estate"] == before + 1
    assert [c.name for c in victim.discard] == ["Estate"]


# --------------------------------------------------------------- Fortress


def test_fortress_returns_to_hand_when_trashed():
    state = _setup()
    player = state.players[0]
    fortress = get_card("Fortress")
    player.hand = [fortress]
    player.hand.remove(fortress)
    state.trash_card(player, fortress)
    assert fortress in player.hand
    assert fortress not in state.trash


# ---------------------------------------------------------------- Goons


def test_goons_scores_a_point_per_buy_while_in_play():
    state = _setup([_PickAI(wants=["Copper"]), _PickAI()])
    player = state.players[0]
    player.goons_played = 2
    player.coins = 3
    player.buys = 2
    state.phase = "buy"
    state.handle_buy_phase()
    assert sum(c.name == "Copper" for c in player.discard) == 2
    assert player.vp_tokens == 4, "two Goons in play, two buys"


def test_goons_discards_opponents_to_three_cards():
    state = _setup()
    player, victim = state.players
    victim.hand = [get_card("Copper") for _ in range(5)]
    get_card("Goons").play_effect(state)
    assert len(victim.hand) == 3


# -------------------------------------------------------------- Sea Hag


def test_sea_hag_puts_the_curse_on_top_of_the_deck():
    state = _setup()
    player, victim = state.players
    victim.deck = [get_card("Copper"), get_card("Silver")]
    get_card("Sea Hag").play_effect(state)
    assert victim.deck[-1].name == "Curse"
    assert [c.name for c in victim.discard] == ["Silver"]


# ------------------------------------------------------------ Old Witch


def test_old_witch_curses_and_lets_the_victim_shed_a_curse_in_hand():
    state = _setup()
    player, victim = state.players
    victim.hand = [get_card("Curse")]
    assert get_card("Old Witch").stats.cards == 3
    get_card("Old Witch").play_effect(state)
    assert [c.name for c in state.trash] == ["Curse"]
    assert sum(c.name == "Curse" for c in victim.discard) == 1


# ---------------------------------------------------------- Scrying Pool


def test_scrying_pool_draws_the_action_run_plus_the_stopper():
    state = _setup()
    player = state.players[0]
    player.deck = [get_card("Copper"), get_card("Fortress"), get_card("Fortress")]
    state.players[1].deck = [get_card("Copper")]
    get_card("Scrying Pool").play_effect(state)
    drawn = [c.name for c in player.hand]
    assert drawn == ["Fortress", "Fortress", "Copper"], drawn
    assert get_card("Scrying Pool").stats.actions == 1


# ----------------------------------------------------------------- Minion


def test_minion_discard_mode_only_hits_hands_of_five_or_more():
    class _MinionAI(_PickAI):
        def choose_minion_mode(self, state, player):
            return "discard"

    state = _setup([_MinionAI(), _PickAI()])
    player, victim = state.players
    player.hand = [get_card("Copper")]
    player.deck = [get_card("Silver") for _ in range(4)]
    victim.hand = [get_card("Copper") for _ in range(4)]
    get_card("Minion").play_effect(state)
    assert len(player.hand) == 4
    assert len(victim.hand) == 4, "a 4-card hand is untouched"
