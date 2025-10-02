import pytest

from dominion.cards.registry import get_card
from dominion.cards.plunder import LOOT_CARD_NAMES
from dominion.cards.base_card import CardType
from dominion.game.game_state import GameState
from tests.utils import ChooseFirstActionAI


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
