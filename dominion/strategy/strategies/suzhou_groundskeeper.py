"""Tunable policies for the Suzhou board, which is built around Groundskeeper.

Board
-----
Crossroads, Great Hall, Mill, Village, Bridge, Ironworks, Groundskeeper,
Laboratory, Market, Nobles.

Groundskeeper pays a VP token for every Victory card gained while it is in
play, and this board is cut so that those tokens are the only reason to gain
Victory cards in bulk: the cheap green is Estate and Great Hall, worth one
point each, and no Gardens or Silk Road pays for mass gaining by itself.

The engine that exploits it has four parts. Great Hall and Mill are cantrips,
so the green does not slow the deck down; Crossroads turns the green back into
draw; Ironworks gains Victory cards during the Action phase, after the
Groundskeepers are in play; Bridge and Market supply the extra Buys (and the
price break) that turn one turn into several gains.

The knobs below are deck caps plus a handful of policy switches. The search
script ``scripts/search_suzhou.py`` plays them against each other, and only
frozen finalists get a ``create_*`` factory.
"""

from collections import Counter

from dominion.cards.registry import get_card
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule


#: Every knob, with the values of the plain engine the search starts from.
DEFAULTS = dict(
    groundskeeper=3,
    ironworks=3,
    bridge=1,
    village=2,
    crossroads=2,
    laboratory=2,
    market=2,
    nobles=0,
    great_hall=99,
    mill=4,
    silver=2,
    gold=99,
    # Turn from which Provinces are bought; Duchies start once the Province
    # pile is down to ``duchy``.
    green=12,
    duchy=4,
    # Spend leftover buys on Estates while a Groundskeeper is in play.
    estate_vp=True,
    # How many Groundskeepers have to be in play before a gain is spent on
    # green rather than on another engine piece. 0 builds the engine out
    # first and takes green with whatever is left over.
    green_gate=1,
    # One card to buy on whichever of the first two turns affords it.
    opening="Ironworks",
)

#: Deck-cap knob for each buyable pile.
CARD_KEYS = {
    "Groundskeeper": "groundskeeper",
    "Ironworks": "ironworks",
    "Laboratory": "laboratory",
    "Market": "market",
    "Bridge": "bridge",
    "Village": "village",
    "Crossroads": "crossroads",
    "Nobles": "nobles",
    "Great Hall": "great_hall",
    "Mill": "mill",
    "Silver": "silver",
    "Gold": "gold",
}

#: Engine pieces in the order the deck wants to add them, money last.
ENGINE_ORDER = (
    "Groundskeeper",
    "Ironworks",
    "Laboratory",
    "Market",
    "Bridge",
    "Village",
    "Crossroads",
    "Nobles",
    "Gold",
    "Silver",
)

#: Points every Victory pile on this board is worth. Nothing here scales with
#: the deck, which is the point of the board: the scaling payload is the
#: Groundskeeper token, not the card.
VICTORY_POINTS = {
    "Province": 6,
    "Duchy": 3,
    "Nobles": 2,
    "Mill": 1,
    "Great Hall": 1,
    "Estate": 1,
}

#: Green the deck gains for points rather than for text, cheapest last.
GREEN = ("Nobles", "Mill", "Great Hall", "Estate")

#: Terminals worth keeping an Action in reserve for.
TERMINALS = frozenset({"Bridge", "Crossroads"})

#: Cards that are dead in hand, so Mill is happy to discard them for $2.
DEAD_IN_HAND = frozenset({"Curse", "Estate", "Duchy", "Province"})


class SuzhouGroundskeeper(EnhancedStrategy):
    """One parameterized deck plan for the Suzhou board."""

    def __init__(self, **params):
        super().__init__()
        unknown = set(params) - DEFAULTS.keys()
        if unknown:
            raise ValueError(f"Unknown parameters: {sorted(unknown)}")
        self.params = DEFAULTS | params
        self.name = "Suzhou Groundskeeper Search Candidate"
        self.description = (
            "Groundskeeper tokens on Ironworks and Workshop gains, with "
            "configurable draw, greening speed and economy."
        )
        active = [
            name
            for name, key in CARD_KEYS.items()
            if self.params[key] or name == self.params["opening"]
        ]
        self.gain_priority = [
            PriorityRule(name) for name in ["Province", "Duchy", "Estate"] + active
        ]
        self.action_priority = [
            PriorityRule(name) for name in active if name not in {"Silver", "Gold"}
        ]
        self.treasure_priority = [
            PriorityRule(name) for name in ("Gold", "Silver", "Copper")
        ]

    # -- helpers -------------------------------------------------------
    @staticmethod
    def pick(choices, names):
        available = {c.name: c for c in choices if c is not None}
        return next((available[n] for n in names if n in available), None)

    def _wants_to_gain(self, state, player):
        """Whether Ironworks or Workshop still has something worth gaining.

        The gain is mandatory once Ironworks is played, and once the cheap
        green is gone a gainer just feeds the deck Silver. Asking the gain
        policy the same question it will be asked a moment later keeps the two
        answers consistent; the ``None`` on the end lets it answer "nothing".

        The $4 limit is compared against the current cost, exactly as
        ``Ironworks.play_effect`` does. ``get_card_cost`` has already applied
        Bridge's discount, so adding ``cost_reduction`` here again would offer
        the policy cards Ironworks cannot actually reach.
        """
        targets = [
            card
            for card in (get_card(name) for name, count in state.supply.items() if count > 0)
            if state.get_card_cost(player, card) <= 4
            and card.cost.potions == 0
            and card.cost.debt == 0
        ]
        return (
            bool(targets)
            and self.choose_gain(state, player, targets + [None], mandatory=True) is not None
        )

    def _greening(self, state, player):
        return (
            player.turns_taken >= self.params["green"]
            or state.supply.get("Province", 8) <= 4
        )

    # -- play order ----------------------------------------------------
    def choose_action(self, state, player, choices):
        """Actions, then draw, then Bridge, then the gainers.

        Ironworks and Workshop hand out their Victory cards during the Action
        phase, so every Groundskeeper played before them is another token on
        every one of those gains -- and Bridge, played before them too, drops
        what they can reach by a dollar.
        """
        victory_in_hand = sum(1 for card in player.hand if card.is_victory)
        names = ["Village"]

        # Crossroads: +1 Card per Victory card in hand, +3 Actions the first
        # time. Leading with it is right while the hand still holds the green
        # it counts; on a thin hand it is a dead terminal.
        if player.crossroads_played == 0 and (
            victory_in_hand >= 2 or player.actions <= 1
        ):
            names.append("Crossroads")

        names += ["Groundskeeper", "Great Hall", "Mill", "Laboratory", "Market", "Nobles"]

        if victory_in_hand:
            names.append("Crossroads")

        names.append("Bridge")
        if self._wants_to_gain(state, player):
            names.append("Ironworks")
        names.append("Crossroads")
        return self.pick(choices, names)

    def choose_card_modes(self, state, player, card, options, minimum, maximum, defaults):
        if card.name == "Nobles":
            # ``True`` is +3 Cards, ``False`` is +2 Actions.
            stranded = player.actions == 0 and any(
                c.name in TERMINALS for c in player.hand
            )
            return [not stranded]
        return defaults

    def choose_treasure(self, state, player, choices):
        return self.pick(choices, ["Gold", "Silver", "Copper"])

    # -- buys and gains ------------------------------------------------
    # Ironworks and Workshop both route their gain through ``choose_buy``,
    # which GeneticAI sends here, so one ranked list covers buys and gains.
    # A buy always offers ``None`` ("buy nothing"); a gainer does not, and
    # that is how this hook tells the two apart.
    def choose_gain(self, state, player, choices, *, mandatory=None):
        p = self.params
        counts = Counter(card.name for card in player.all_cards())
        provinces = state.supply.get("Province", 8)
        greening = self._greening(state, player)
        tokens = getattr(player, "groundskeeper_bonus", 0)
        if mandatory is None:
            mandatory = not any(card is None for card in choices)
        names = []

        # ``opening`` names one card the deck wants early, and takes it on
        # whichever of the first two turns can afford it -- not one copy per
        # turn. ``turns_taken`` is incremented at the start of each turn, so
        # the player's first two turns are 1 and 2, and the ownership check is
        # what stops a $5 second turn from buying a second $3 opener instead
        # of the Groundskeeper at the top of ``ENGINE_ORDER``.
        if player.turns_taken <= 2 and p["opening"] and not counts[p["opening"]]:
            names.append(p["opening"])

        # A Victory card gained before the Groundskeepers are in play scores
        # no token, so ``green_gate`` asks how many of them to wait for.
        gate_met = tokens >= p["green_gate"]

        # Green outranks the engine on a free gain and on a second or later
        # buy, but never on the turn's main buy while the engine is still
        # being built: a $5 hand that takes a $3 Great Hall over a Laboratory
        # has thrown two dollars away, and that is how a Groundskeeper deck
        # ends up with five Groundskeepers and no draw.
        spare_buy = getattr(player, "cards_gained_this_buy_phase", 0) >= 1
        green_first = greening or (gate_met and (mandatory or spare_buy))

        green = []
        if gate_met or greening:
            for name in GREEN:
                if name in CARD_KEYS and counts[name] >= p[CARD_KEYS[name]]:
                    continue
                if name == "Estate" and not (p["estate_vp"] and tokens):
                    continue
                green.append(name)
            green.sort(key=lambda name: -VICTORY_POINTS[name])

        engine = [name for name in ENGINE_ORDER if counts[name] < p[CARD_KEYS[name]]]

        if greening:
            top = ["Province"]
            if provinces <= p["duchy"] or tokens:
                top.append("Duchy")
            names += top + green + engine
        elif green_first:
            names += green + engine
        else:
            names += engine + green

        pick = self.pick(choices, names)
        if pick is not None or any(card is None for card in choices):
            return pick
        # A gainer's choice is not optional. Take the best Victory card on
        # offer, then the best Treasure, then anything at all.
        return self._forced_gain(choices, tokens)

    def choose_cards_to_discard(self, state, player, choices, count, *, reason=None):
        """Mill's discard is optional, so only pay it with dead cards.

        Two Estates for two coins is a good trade in a deck that gains Estates
        for their tokens; two Coppers for two coins is a wash, and anything
        else is a loss.
        """
        if reason != "mill":
            return super().choose_cards_to_discard(
                state, player, choices, count, reason=reason
            )
        dead = [card for card in choices if card.name in DEAD_IN_HAND]
        dead.sort(key=lambda card: (VICTORY_POINTS.get(card.name, 0), card.name))
        return dead[:count] if len(dead) >= count else []

    @staticmethod
    def _forced_gain(choices, tokens):
        real = [card for card in choices if card is not None]
        if not real:
            return None
        victory = [card for card in real if card.is_victory]
        if victory:
            return max(
                victory,
                key=lambda c: (VICTORY_POINTS.get(c.name, 0) + tokens, c.cost.coins),
            )
        return max(real, key=lambda c: (c.is_treasure, c.cost.coins, c.name))


#: Winner of the twelve-entrant finalist round robin (200 games per pairing),
#: frozen before validation. ``scripts/search_suzhou.py`` reproduces it.
WINNER = dict(
    groundskeeper=3,
    ironworks=3,
    laboratory=2,
    market=2,
    bridge=1,
    village=2,
    crossroads=3,
    nobles=0,
    great_hall=99,
    mill=4,
    silver=2,
    gold=99,
    green=12,
    duchy=4,
    estate_vp=True,
    green_gate=0,
    opening="Ironworks",
)


def create_suzhou_groundskeeper_engine() -> EnhancedStrategy:
    """Three Groundskeepers, three Ironworks, and every cheap Victory pile.

    The plan spends the main buy of each turn on the engine and every spare
    Buy -- and every Ironworks play -- on a Victory card, so the Groundskeepers
    already in play turn each one into points. Against its own one-field
    ablation with ``groundskeeper=0`` it scored 96.0% over 400 games.
    """

    strategy = SuzhouGroundskeeper(**WINNER)
    strategy.name = "Suzhou Groundskeeper Engine"
    strategy.description = (
        "Great Hall, Mill and Estate gains under three Groundskeepers, with "
        "Ironworks gaining in the Action phase and Crossroads drawing the "
        "green back. See the Suzhou board guide."
    )
    return strategy
