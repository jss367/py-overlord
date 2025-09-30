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


def test_hammer_respects_gain_choice():
    class HammerAI(ChooseFirstActionAI):
        def choose_treasure(self, state, choices):
            for card in choices:
                if card and card.name == "Hammer":
                    return card
            return None

        def choose_buy(self, state, choices):
            for card in choices:
                if card and card.name == "Village":
                    return card
            return None

    ai = HammerAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village"), get_card("Workshop")])
    player = state.players[0]

    hammer = get_card("Hammer")
    player.hand = [hammer]
    player.deck = []
    player.discard = []

    starting_villages = state.supply["Village"]

    state.phase = "treasure"
    state.handle_treasure_phase()

    assert state.supply["Village"] == starting_villages - 1
    assert any(card.name == "Village" for card in player.discard)
    assert not any(card.name == "Workshop" for card in player.discard)


def test_insignia_allows_declining_topdeck():
    class InsigniaAI(ChooseFirstActionAI):
        def choose_treasure(self, state, choices):
            for card in choices:
                if card and card.name == "Insignia":
                    return card
            return None

        def choose_buy(self, state, choices):
            for card in choices:
                if card and card.name == "Village":
                    return card
            return None

        def should_topdeck_gain(self, state, player, gained_card):
            return False

    ai = InsigniaAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]

    insignia = get_card("Insignia")
    player.hand = [insignia]
    player.deck = []
    player.discard = []

    state.phase = "treasure"
    state.handle_treasure_phase()
    state.handle_buy_phase()

    assert any(card.name == "Village" for card in player.discard)
    assert not any(card.name == "Village" for card in player.deck)


def test_jewels_moves_to_bottom_on_duration():
    state = GameState(players=[])
    state.initialize_game([ChooseFirstActionAI()], [get_card("Village")])
    player = state.players[0]

    jewels = get_card("Jewels")
    copper = get_card("Copper")
    silver = get_card("Silver")
    gold = get_card("Gold")

    player.duration = [jewels]
    player.deck = [copper, silver, gold]

    jewels.on_duration(state)

    drawn_order: list[str] = []
    while player.deck:
        drawn_order.extend(card.name for card in player.draw_cards(1))

    assert drawn_order[:3] == ["Gold", "Silver", "Copper"]
    assert drawn_order[-1] == "Jewels"


def test_puzzle_box_returns_card_at_end_of_turn():
    class PuzzleBoxAI(ChooseFirstActionAI):
        def choose_treasure(self, state, choices):
            for card in choices:
                if card and card.name == "Puzzle Box":
                    return card
            return None

        def choose_card_to_set_aside(self, state, player, cards, *, reason=None):
            for card in cards:
                if card.name == "Estate":
                    return card
            return None

    ai = PuzzleBoxAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]

    estate = get_card("Estate")
    puzzle_box = get_card("Puzzle Box")
    player.hand = [puzzle_box, estate]
    player.deck = [get_card("Copper") for _ in range(5)]
    player.discard = []

    state.phase = "treasure"
    state.handle_treasure_phase()
    assert estate not in player.hand
    assert estate not in player.discard

    state.handle_buy_phase()
    state.handle_cleanup_phase()

    assert any(card.name == "Estate" for card in player.hand)
    assert not any(card.name == "Estate" for card in player.discard)


def test_sextant_allows_player_choices():
    class SextantAI(ChooseFirstActionAI):
        def choose_treasure(self, state, choices):
            for card in choices:
                if card and card.name == "Sextant":
                    return card
            return None

        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            return [card for card in choices if card.name == "Estate"]

        def order_cards_for_sextant(self, state, player, cards):
            by_name = {card.name: card for card in cards}
            order = ["Province", "Gold", "Silver", "Copper"]
            return [by_name[name] for name in order if name in by_name]

    ai = SextantAI()
    state = GameState(players=[])
    state.initialize_game([ai], [get_card("Village")])
    player = state.players[0]

    sextant = get_card("Sextant")
    player.hand = [sextant]
    player.deck = [
        get_card("Copper"),
        get_card("Silver"),
        get_card("Estate"),
        get_card("Gold"),
        get_card("Province"),
    ]
    player.discard = []

    state.phase = "treasure"
    state.handle_treasure_phase()

    assert any(card.name == "Estate" for card in player.discard)
    drawn = [player.draw_cards(1)[0].name for _ in range(4)]
    assert drawn == ["Province", "Gold", "Silver", "Copper"]


def test_sword_allows_discard_choice():
    class SwordAttackAI(ChooseFirstActionAI):
        def choose_treasure(self, state, choices):
            for card in choices:
                if card and card.name == "Sword":
                    return card
            return None

    class SwordDefenseAI(ChooseFirstActionAI):
        def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
            for card in choices:
                if card.name == "Estate":
                    return [card]
            return super().choose_cards_to_discard(state, player, choices, count, reason=reason)

    attacker = SwordAttackAI()
    defender = SwordDefenseAI()
    state = GameState(players=[])
    state.initialize_game([attacker, defender], [get_card("Village")])
    p1, p2 = state.players

    sword = get_card("Sword")
    p1.hand = [sword]
    p2.hand = [
        get_card("Gold"),
        get_card("Silver"),
        get_card("Copper"),
        get_card("Estate"),
        get_card("Province"),
    ]

    state.phase = "treasure"
    state.handle_treasure_phase()

    assert len(p2.hand) == 4
    assert any(card.name == "Estate" for card in p2.discard)
