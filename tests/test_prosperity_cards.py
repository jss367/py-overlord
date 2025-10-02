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

