"""Tests for the five Allies split piles."""

from dominion.cards.allies.augurs import AUGURS_PILE_ORDER
from dominion.cards.allies.clashes import CLASHES_PILE_ORDER
from dominion.cards.allies.forts import FORTS_PILE_ORDER
from dominion.cards.allies.odysseys import ODYSSEYS_PILE_ORDER
from dominion.cards.allies.townsfolk import TOWNSFOLK_PILE_ORDER
from dominion.cards.allies._split_base import AlliesSplitCard
from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class _PlayFirstActionAI(DummyAI):
    def choose_action(self, state, choices):
        for card in choices:
            if card is not None and card.is_action:
                return card
        return None


def _setup_state(top_card_name: str) -> tuple[GameState, PlayerState]:
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    top = get_card(top_card_name)
    state.setup_supply([top])
    return state, player


class _NamingAI(DummyAI):
    def __init__(self, named: str):
        super().__init__()
        self.named = named

    def name_card_for_wishing_well(self, state, player):
        return self.named


def _setup_sorceress_state(named: str) -> tuple[GameState, PlayerState, PlayerState]:
    attacker = PlayerState(_NamingAI(named))
    defender = PlayerState(DummyAI())
    state = GameState(players=[attacker, defender])
    state.setup_supply([get_card("Herb Gatherer")])
    return state, attacker, defender


def test_all_split_piles_have_four_cards():
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        assert len(order) == 4
        for name in order:
            card = get_card(name)
            assert isinstance(card, AlliesSplitCard)


def test_setup_supply_creates_all_partner_piles():
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        state, _ = _setup_state(order[0])
        for name in order:
            assert name in state.supply, f"Pile {name} missing from supply for {order[0]}"
            assert state.supply[name] > 0


def test_only_top_card_buyable():
    """The first pile-member is buyable; lower ones are not until top empties."""
    for order in (
        AUGURS_PILE_ORDER,
        CLASHES_PILE_ORDER,
        FORTS_PILE_ORDER,
        ODYSSEYS_PILE_ORDER,
        TOWNSFOLK_PILE_ORDER,
    ):
        state, _ = _setup_state(order[0])
        top = get_card(order[0])
        assert top.may_be_bought(state)
        for lower in order[1:]:
            assert not get_card(lower).may_be_bought(state)


def test_top_drained_exposes_next():
    state, _ = _setup_state("Town Crier")
    state.supply["Town Crier"] = 0
    blacksmith = get_card("Blacksmith")
    assert blacksmith.may_be_bought(state)


def test_townsfolk_grant_favor():
    for name in TOWNSFOLK_PILE_ORDER:
        state, player = _setup_state("Town Crier")
        card = get_card(name)
        player.in_play.append(card)
        before = player.favors
        # Skip Elder which expects an action in hand; stub a no-op hand.
        if name == "Elder":
            card.play_effect(state)
        else:
            card.on_play(state)
        assert player.favors >= before + 1


def test_elder_gives_townsfolk_choice_card_one_extra_mode():
    class ChooseBlacksmithAI(DummyAI):
        def choose_action(self, state, choices):
            for choice in choices:
                if choice is not None and choice.name == "Blacksmith":
                    return choice
            return None

    player = PlayerState(ChooseBlacksmithAI())
    state = GameState(players=[player])
    state.setup_supply([get_card("Town Crier")])
    player.actions = 0
    player.hand = [
        get_card("Blacksmith"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
        get_card("Estate"),
    ]
    player.deck = [get_card("Copper"), get_card("Silver"), get_card("Gold")]

    elder = get_card("Elder")
    player.in_play.append(elder)
    elder.on_play(state)

    assert player.favors == 2
    assert player.actions == 2
    assert len(player.hand) == 7
    assert not hasattr(state, "_elder_extra_townsfolk_choices")


def test_clashes_grant_favor():
    for name in CLASHES_PILE_ORDER:
        state, player = _setup_state("Battle Plan")
        card = get_card(name)
        if not card.is_action:
            # Territory is a Victory; doesn't fire on_play.
            continue
        player.in_play.append(card)
        before = player.favors
        if name == "Battle Plan":
            # +1 Card requires deck contents — skip the +1 Card draw.
            card.play_effect(state)
        else:
            card.play_effect(state)
        assert player.favors >= before + 1


def test_garrison_tokens_each_card_gained_and_draws_next_turn():
    state, player = _setup_state("Tent")
    garrison = get_card("Garrison")
    player.in_play.append(garrison)
    garrison.on_play(state)

    state.gain_card(player, get_card("Silver"))
    state.gain_card(player, get_card("Estate"))

    assert garrison.tokens == 2
    assert garrison in player.duration
    assert player.actions == 2
    assert player.buys == 2

    player.deck = [get_card("Copper") for _ in range(5)]
    player.hand = []
    state.handle_cleanup_phase()

    assert garrison in player.duration
    assert garrison in player.in_play

    cards_before_duration = len(player.hand)
    state.do_duration_phase()

    assert len(player.hand) == cards_before_duration + 2
    assert garrison.tokens == 0
    assert garrison not in player.duration
    assert garrison in player.discard
    assert garrison.duration_persistent is False


def test_garrison_without_tokens_discards_during_cleanup():
    state, player = _setup_state("Tent")
    garrison = get_card("Garrison")
    player.in_play.append(garrison)
    garrison.on_play(state)
    player.deck = [get_card("Copper") for _ in range(5)]

    assert garrison.tokens == 0
    assert garrison not in player.duration

    state.handle_cleanup_phase()

    assert garrison not in player.duration
    assert garrison not in player.in_play
    assert garrison in player.discard


def test_garrison_played_twice_adds_two_tokens_per_gain():
    state, player = _setup_state("Tent")
    garrison = get_card("Garrison")
    player.in_play.append(garrison)

    garrison.on_play(state)
    garrison.on_play(state)
    state.gain_card(player, get_card("Silver"))

    assert garrison.tokens == 2
    assert player.duration == [garrison]

    player.deck = [get_card("Copper"), get_card("Gold")]
    player.hand = []

    state.do_duration_phase()

    assert len(player.hand) == 2
    assert garrison.tokens == 0


def test_warlord_blocks_opponent_third_same_named_action():
    attacker = PlayerState(DummyAI())
    opponent = PlayerState(_PlayFirstActionAI())
    state = GameState(players=[attacker, opponent])
    state.current_player_index = 0

    warlord = get_card("Warlord")
    warlord.play_effect(state)

    state.current_player_index = 1
    third_smithy = get_card("Smithy")
    opponent.actions = 1
    opponent.in_play = [get_card("Smithy"), get_card("Smithy")]
    opponent.hand = [third_smithy]
    opponent.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()

    assert third_smithy in opponent.hand
    assert third_smithy not in opponent.in_play
    assert opponent.actions == 1


def test_warlord_allows_opponent_second_same_named_action():
    attacker = PlayerState(DummyAI())
    opponent = PlayerState(_PlayFirstActionAI())
    state = GameState(players=[attacker, opponent])
    state.current_player_index = 0

    warlord = get_card("Warlord")
    warlord.play_effect(state)

    state.current_player_index = 1
    second_smithy = get_card("Smithy")
    opponent.actions = 1
    opponent.in_play = [get_card("Smithy")]
    opponent.hand = [second_smithy]
    opponent.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()

    assert second_smithy not in opponent.hand
    assert second_smithy in opponent.in_play


def test_warlord_restriction_ends_on_duration():
    attacker = PlayerState(DummyAI())
    opponent = PlayerState(_PlayFirstActionAI())
    state = GameState(players=[attacker, opponent])
    state.current_player_index = 0

    warlord = get_card("Warlord")
    warlord.play_effect(state)
    assert getattr(opponent, "warlord_restriction_count", 0) == 1

    warlord.on_duration(state)
    assert getattr(opponent, "warlord_restriction_count", 0) == 0

    state.current_player_index = 1
    third_smithy = get_card("Smithy")
    opponent.actions = 1
    opponent.in_play = [get_card("Smithy"), get_card("Smithy")]
    opponent.hand = [third_smithy]
    opponent.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()

    assert third_smithy not in opponent.hand
    assert third_smithy in opponent.in_play


def test_warlord_blocked_indirect_play_returns_card_to_hand():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    player.warlord_restriction_count = 1
    third_smithy = get_card("Smithy")
    player.hand = [third_smithy]
    player.in_play = [get_card("Smithy"), get_card("Smithy")]
    assert state.move_card_from_hand_to_play(player, third_smithy)

    state.play_action_indirectly(player, third_smithy)

    assert third_smithy in player.hand
    assert third_smithy not in player.in_play
    assert player.actions_this_turn == 0


def test_warlord_blocked_indirect_play_without_hand_source_does_not_enter_hand():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    player.warlord_restriction_count = 1
    revealed_smithy = get_card("Smithy")
    player.in_play = [get_card("Smithy"), get_card("Smithy"), revealed_smithy]

    state.play_action_indirectly(player, revealed_smithy)

    assert revealed_smithy not in player.hand
    assert revealed_smithy not in player.in_play
    assert player.actions_this_turn == 0


def test_warlord_blocks_inherited_estate_as_third_copy():
    player = PlayerState(_PlayFirstActionAI())
    state = GameState(players=[player])
    player.warlord_restriction_count = 1
    player.inherited_action_name = "Smithy"
    third_estate = get_card("Estate")
    player.actions = 1
    player.in_play = [get_card("Estate"), get_card("Estate")]
    player.hand = [third_estate]
    player.deck = [get_card("Copper") for _ in range(5)]

    state.handle_action_phase()

    assert third_estate in player.hand
    assert third_estate not in player.in_play


def test_sorceress_matching_reveal_curses_each_other_player():
    state, attacker, defender = _setup_sorceress_state("Silver")
    bottom = get_card("Copper")
    revealed = get_card("Silver")
    attacker.deck = [bottom, revealed]
    curse_count = state.supply["Curse"]

    sorceress = get_card("Sorceress")
    sorceress.on_play(state)

    assert sorceress.is_attack
    assert attacker.hand[-1] is revealed
    assert attacker.deck == [bottom]
    assert state.supply["Curse"] == curse_count - 1
    assert any(card.name == "Curse" for card in defender.discard)
    assert all(card.name != "Curse" for card in attacker.discard)


def test_sorceress_mismatched_reveal_does_not_curse():
    state, attacker, defender = _setup_sorceress_state("Gold")
    revealed = get_card("Silver")
    attacker.deck = [revealed]
    curse_count = state.supply["Curse"]

    get_card("Sorceress").on_play(state)

    assert attacker.hand[-1] is revealed
    assert attacker.deck == []
    assert state.supply["Curse"] == curse_count
    assert all(card.name != "Curse" for card in defender.discard)


def test_distant_shore_gains_two_estates_on_gain():
    state, player = _setup_state("Old Map")
    state.supply["Estate"] = 8
    distant = get_card("Distant Shore")
    state.gain_card(player, distant)
    estates_in_discard = sum(1 for c in player.discard if c.name == "Estate")
    assert estates_in_discard == 2


def test_territory_gains_gold_per_empty_pile():
    state, player = _setup_state("Battle Plan")
    state.supply["Gold"] = 5
    state.supply["Workshop"] = 0  # one empty pile
    state.supply["Smithy"] = 0  # another empty pile
    territory = get_card("Territory")
    state.gain_card(player, territory)
    golds = sum(1 for c in player.discard if c.name == "Gold")
    assert golds == state.empty_piles or golds >= 2


def test_old_map_discards_and_redraws():
    state, player = _setup_state("Old Map")
    player.deck = [get_card("Copper"), get_card("Silver"), get_card("Gold")]
    player.hand = [get_card("Estate")]

    class DiscardAI(DummyAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            estates = [c for c in choices if c.name == "Estate"]
            return estates[:count]

    player.ai = DiscardAI()
    old_map = get_card("Old Map")
    player.in_play.append(old_map)
    old_map.on_play(state)
    # +1 Card from stats, then discard 1, +1 Card from play_effect.
    assert any(c.name == "Estate" for c in player.discard)
    assert len(player.hand) >= 1
