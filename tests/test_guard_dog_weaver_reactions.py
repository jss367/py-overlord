from dominion.cards.registry import get_card
from dominion.game.game_state import GameState
from dominion.game.player_state import PlayerState

from tests.utils import DummyAI


class DeclineGuardDogAI(DummyAI):
    def should_play_guard_dog(self, state, player, card):  # type: ignore[override]
        return False


class DeclineWeaverAI(DummyAI):
    def should_play_weaver_on_discard(self, state, player, card):  # type: ignore[override]
        return False


def test_guard_dog_reaction_respects_ai_choice():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DeclineGuardDogAI())
    state = GameState(players=[attacker, defender])

    guard_dog = get_card("Guard Dog")
    defender.hand = [guard_dog]
    defender.deck = [get_card("Copper"), get_card("Estate"), get_card("Silver")]
    defender.hit = False

    def mark_attack(target):
        target.hit = True

    state.attack_player(defender, mark_attack)

    assert defender.hit is True
    assert guard_dog in defender.hand
    assert guard_dog not in defender.in_play
    assert len(defender.hand) == 1


def test_guard_dog_reaction_plays_when_allowed():
    attacker = PlayerState(DummyAI())
    defender = PlayerState(DummyAI())
    state = GameState(players=[attacker, defender])

    guard_dog = get_card("Guard Dog")
    defender.hand = [guard_dog]
    defender.deck = [get_card("Copper"), get_card("Estate"), get_card("Silver"), get_card("Gold")]

    defender.hit = False

    def mark_attack(target):
        target.hit = True

    state.attack_player(defender, mark_attack)

    assert defender.hit is True
    assert guard_dog not in defender.hand
    assert guard_dog in defender.in_play


def test_weaver_discard_reaction_respects_ai_choice():
    player = PlayerState(DeclineWeaverAI())
    state = GameState(players=[player])
    state.supply["Silver"] = 10

    weaver = get_card("Weaver")
    player.hand = [weaver]
    player.hand.remove(weaver)

    state.discard_card(player, weaver)

    assert weaver in player.discard
    assert weaver not in player.in_play


def test_weaver_discard_reaction_plays_when_allowed():
    player = PlayerState(DummyAI())
    state = GameState(players=[player])
    state.supply["Silver"] = 10

    weaver = get_card("Weaver")
    player.hand = [weaver]
    player.hand.remove(weaver)

    state.discard_card(player, weaver)

    assert weaver in player.in_play
    silver_count = sum(1 for card in player.discard if card.name == "Silver")
    assert silver_count == 2
