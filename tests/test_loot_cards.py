import pytest

from dominion.cards.registry import get_card
from dominion.cards.plunder import LOOT_CARD_NAMES
from dominion.cards.base_card import CardType
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState
from tests.utils import ChooseFirstActionAI, DummyAI, TrashFirstAI


def test_loot_cards_all_defined():
    assert len(LOOT_CARD_NAMES) == 15
    for name in LOOT_CARD_NAMES:
        card = get_card(name)
        assert CardType.TREASURE in card.types


def test_sword_and_shield_types():
    shield = get_card("Shield")
    assert CardType.REACTION in shield.types

    sword = get_card("Sword")
    assert CardType.ATTACK in sword.types


def test_shield_blocks_witch_attack():
    attacker = ChooseFirstActionAI()
    defender = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([attacker, defender], [get_card("Witch")])

    p1, p2 = state.players
    p1.hand = [get_card("Witch")]
    p2.hand = [get_card("Shield")]
    state.phase = "action"
    state.handle_action_phase()

    assert not any(c.name == "Curse" for c in p2.discard)


class SextantDecisionAI(ChooseFirstActionAI):
    def __init__(self, discard_plan, order_plan):
        super().__init__()
        self.discard_plan = list(discard_plan)
        self.order_plan = list(order_plan)

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        available = list(choices)
        selected = []
        for name in self.discard_plan:
            if len(selected) >= count:
                break
            for card in list(available):
                if card.name == name:
                    selected.append(card)
                    available.remove(card)
                    break
        return selected

    def order_cards_for_topdeck(self, state, player, cards):
        ordered = []
        remaining = list(cards)
        for name in self.order_plan:
            for card in list(remaining):
                if card.name == name:
                    ordered.append(card)
                    remaining.remove(card)
                    break
        ordered.extend(remaining)
        return ordered


@pytest.mark.parametrize(
    "discard_plan, order_plan, expected_deck, expected_discard",
    [
        (
            [],
            ["Estate", "Copper", "Gold", "Silver", "Duchy"],
            ["Province", "Duchy", "Silver", "Gold", "Copper", "Estate"],
            [],
        ),
        (
            ["Gold", "Estate"],
            ["Silver", "Copper", "Duchy"],
            ["Province", "Duchy", "Copper", "Silver"],
            ["Gold", "Estate"],
        ),
        (
            ["Gold", "Duchy", "Silver", "Estate", "Copper"],
            [],
            ["Province"],
            ["Gold", "Duchy", "Silver", "Estate", "Copper"],
        ),
    ],
)
def test_sextant_respects_ai_discard_and_order(
    discard_plan, order_plan, expected_deck, expected_discard
):
    ai = SextantDecisionAI(discard_plan, order_plan)
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Sextant")])

    player = state.players[0]
    player.hand = []
    player.discard = []
    player.deck = [
        get_card("Province"),
        get_card("Copper"),
        get_card("Estate"),
        get_card("Silver"),
        get_card("Duchy"),
        get_card("Gold"),
    ]

    sextant = get_card("Sextant")
    sextant.play_effect(state)

    assert [card.name for card in player.deck] == expected_deck
    assert [card.name for card in player.discard] == expected_discard

def test_jewels_returns_to_bottom_of_deck_after_duration():
    state = GameState(players=[])
    state.initialize_game([ChooseFirstActionAI()], [get_card("Village")])

    player = state.players[0]
    jewels = get_card("Jewels")
    existing = [get_card("Copper"), get_card("Estate")]

    player.deck = existing.copy()
    player.duration = [jewels]

    jewels.on_duration(state)

    assert jewels not in player.duration
    assert player.deck == existing + [jewels]

def test_prize_goat_trash_and_decline():
    # Trashing scenario - AI trashes the first available card
    trashing_ai = TrashFirstAI()
    trashing_player = PlayerState(ai=trashing_ai)
    state_trash = GameState(players=[trashing_player])
    trashed_card = get_card("Copper")
    trashing_player.hand = [trashed_card]

    prize_goat = get_card("Prize Goat")
    prize_goat.play_effect(state_trash)

    assert trashed_card not in trashing_player.hand
    assert trashed_card in state_trash.trash

    # Decline scenario - AI chooses the None option to skip trashing
    class DeclineTrashAI(DummyAI):
        def __init__(self):
            super().__init__()
            self.last_choices = None

        def choose_card_to_trash(self, state, choices):
            self.last_choices = list(choices)
            return choices[-1] if choices else None

    decline_ai = DeclineTrashAI()
    decline_player = PlayerState(ai=decline_ai)
    state_decline = GameState(players=[decline_player])
    keep_card = get_card("Estate")
    decline_player.hand = [keep_card]

    prize_goat_skip = get_card("Prize Goat")
    prize_goat_skip.play_effect(state_decline)

    assert keep_card in decline_player.hand
    assert keep_card not in state_decline.trash
    assert decline_ai.last_choices is not None
    assert None in decline_ai.last_choices

def test_sword_attack_discards_low_value_cards_first():
    attacker = ChooseFirstActionAI()
    defender = ChooseFirstActionAI()
    state = GameState(players=[])
    state.initialize_game([attacker, defender], [get_card("Sword")])

    sword = get_card("Sword")
    gold = get_card("Gold")
    province = get_card("Province")
    silver = get_card("Silver")
    estate = get_card("Estate")
    copper = get_card("Copper")

    attacker_state, defender_state = state.players
    state.current_player_index = 0
    attacker_state.hand = [sword]
    defender_state.hand = [gold, province, silver, estate, copper]
    defender_state.discard = []

    sword.play_effect(state)

    assert len(defender_state.hand) == 4
    assert any(card.name == "Estate" for card in defender_state.discard)
    assert all(card.name != "Gold" for card in defender_state.discard)
    assert any(card.name == "Gold" for card in defender_state.hand)

