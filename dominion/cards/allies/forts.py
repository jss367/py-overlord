"""Forts split pile (Allies). Top to bottom: Tent, Garrison, Hill Fort,
Stronghold."""

from typing import ClassVar

from ..base_card import Card, CardCost, CardStats, CardType
from ._rules import candidates, gain, plus_cards, plus_coins, rotate, select_modes
from ._split_base import AlliesSplitCard

FORTS_PILE_ORDER = ("Tent", "Garrison", "Hill Fort", "Stronghold")


class _Forts(AlliesSplitCard):
    pile_order: ClassVar[tuple[str, ...]] = FORTS_PILE_ORDER


class Tent(_Forts):
    def __init__(self):
        super().__init__(
            name="Tent",
            cost=CardCost(coins=3),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        rotate(game_state, p, "Tent")


class Garrison(_Forts):
    """+$2. This turn, when you gain a card, add a token here.
    At the start of your next turn, remove them for +1 Card each.
    """

    upper_partners: ClassVar[tuple[str, ...]] = ("Tent",)

    def __init__(self):
        super().__init__(
            name="Garrison",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.tokens = 0
        self._garrison_gain_triggers = 0
        self._garrison_turn_marker = None
        self._garrison_last_gain_marker = None

    def play_effect(self, game_state):
        player = game_state.current_player
        turn_marker = (game_state.players.index(player), player.turns_taken)
        if self._garrison_turn_marker != turn_marker:
            self.tokens = 0
            self._garrison_gain_triggers = 0
            self._garrison_last_gain_marker = None
            self._garrison_turn_marker = turn_marker
        self._garrison_gain_triggers += 1
        self.duration_persistent = False

    def on_owner_gain(self, game_state, player, gained_card: Card) -> None:
        if self not in player.in_play or self._garrison_gain_triggers <= 0:
            return
        if self._garrison_turn_marker != (
            game_state.players.index(player),
            player.turns_taken,
        ):
            return

        gain_marker = (
            game_state.players.index(player),
            getattr(player, "cards_gained_this_turn", 0),
            gained_card,
        )
        if self._garrison_last_gain_marker == gain_marker:
            return

        self._garrison_last_gain_marker = gain_marker
        self.tokens += self._garrison_gain_triggers
        self.duration_persistent = True
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        tokens = self.tokens
        if tokens > 0:
            game_state.draw_cards(player, tokens)
        self.tokens = 0
        self._garrison_gain_triggers = 0
        self._garrison_last_gain_marker = None
        self.duration_persistent = False


class HillFort(_Forts):
    def __init__(self):
        super().__init__(
            name="Hill Fort",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        gained = gain(game_state, p, candidates(game_state, CardCost(coins=4)))
        default = "hand" if gained is not None else "cycle"
        for mode in select_modes(game_state, p, self, ["hand", "cycle"], [default]):
            if mode == "hand":
                for zone in [game_state.gain_destination(gained)]:
                    if zone is not None and gained in zone:
                        zone.remove(gained)
                        p.hand.append(gained)
                        break
            else:
                plus_cards(game_state, p, 1)
                if not p.ignore_action_bonuses:
                    p.actions += 1


class Stronghold(_Forts):
    def __init__(self):
        super().__init__(
            name="Stronghold",
            cost=CardCost(coins=6),
            stats=CardStats(vp=2),
            types=[CardType.ACTION, CardType.DURATION, CardType.VICTORY],
        )

    def play_effect(self, game_state):
        p = game_state.current_player
        for mode in select_modes(
            game_state, p, self, ["coins", "cards_next_turn"], ["cards_next_turn"]
        ):
            if mode == "coins":
                plus_coins(p, 3)
            else:
                p.duration.append(self)

    def on_duration(self, game_state):
        game_state.draw_cards(game_state.current_player, 3)
