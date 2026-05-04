"""Empires Landmarks (20 total)."""

from collections import Counter

from dominion.cards.base_card import CardType

from .base_landmark import Landmark


# ---------------------------------------------------------------------------
# Landmarks that move VP between piles


class Aqueduct(Landmark):
    """When you gain a Treasure, move 1 VP from its pile to here. When you
    gain a Victory card, take VP from here. Setup: place 1 VP on each
    Treasure pile that has VP markers (Silver, Gold) — 8 each per official
    setup.
    """

    def __init__(self):
        super().__init__(
            name="Aqueduct",
            description=(
                "When gaining a Treasure, move 1 VP from its pile to Aqueduct. "
                "When gaining a Victory card, take VP from Aqueduct."
            ),
        )

    def setup(self, game_state) -> None:
        # Official Empires setup: place 8 VP on Silver, 8 VP on Gold piles.
        self.pile_vp = {"Silver": 8, "Gold": 8}
        self.vp_pool = 0

    def on_gain(self, game_state, player, card) -> None:
        if card.is_treasure and self.pile_vp.get(card.name, 0) > 0:
            self.pile_vp[card.name] -= 1
            self.vp_pool += 1
        if card.is_victory:
            player.vp_tokens += self.vp_pool
            self.vp_pool = 0


class Arena(Landmark):
    """Start of Buy phase: may discard an Action for +2 VP from here.
    Setup: 6 VP per player on Arena."""

    def __init__(self):
        super().__init__(
            name="Arena",
            description="Start of Buy: discard an Action for +2 VP from Arena.",
        )

    def setup(self, game_state) -> None:
        self.vp_pool = 6 * len(game_state.players)

    def on_buy_phase_start(self, game_state, player) -> None:
        if self.vp_pool < 2:
            return
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        # Default: discard the cheapest action (or AI hook in the future).
        chosen = min(actions, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(chosen)
        game_state.discard_card(player, chosen)
        take = min(2, self.vp_pool)
        self.vp_pool -= take
        player.vp_tokens += take


class BanditFort(Landmark):
    """At end of game: -2 VP per Silver/Gold each player has."""

    def __init__(self):
        super().__init__(
            name="Bandit Fort",
            description="-2 VP per Silver and Gold at end of game.",
        )

    def vp_for(self, game_state, player) -> int:
        count = sum(1 for c in player.all_cards() if c.name in ("Silver", "Gold"))
        return -2 * count


class Basilica(Landmark):
    """When you buy a card, if you have $2+ left, +2 VP from here.
    Setup: 6 VP per player."""

    def __init__(self):
        super().__init__(
            name="Basilica",
            description="When buying with $2+ left over, +2 VP from Basilica.",
        )

    def setup(self, game_state) -> None:
        self.vp_pool = 6 * len(game_state.players)

    def on_buy(self, game_state, player, card) -> None:
        if self.vp_pool <= 0:
            return
        if player.coins >= 2:
            take = min(2, self.vp_pool)
            self.vp_pool -= take
            player.vp_tokens += take


class Battlefield(Landmark):
    """When you gain a Victory card, +2 VP from here.
    Setup: 6 VP per player."""

    def __init__(self):
        super().__init__(
            name="Battlefield",
            description="On gaining a Victory card, +2 VP from Battlefield.",
        )

    def setup(self, game_state) -> None:
        self.vp_pool = 6 * len(game_state.players)

    def on_gain(self, game_state, player, card) -> None:
        if not card.is_victory:
            return
        if self.vp_pool <= 0:
            return
        take = min(2, self.vp_pool)
        self.vp_pool -= take
        player.vp_tokens += take


class Colonnade(Landmark):
    """When you buy an Action, if you have a copy in play, +2 VP from here.
    Setup: 6 VP per player."""

    def __init__(self):
        super().__init__(
            name="Colonnade",
            description="On buying an Action you have in play, +2 VP from Colonnade.",
        )

    def setup(self, game_state) -> None:
        self.vp_pool = 6 * len(game_state.players)

    def on_buy(self, game_state, player, card) -> None:
        if self.vp_pool <= 0:
            return
        if not card.is_action:
            return
        if any(c.name == card.name for c in player.in_play):
            take = min(2, self.vp_pool)
            self.vp_pool -= take
            player.vp_tokens += take


class DefiledShrine(Landmark):
    """When you gain an Action (not from supply pile), move 1 VP from its
    pile to here. When you buy a Curse, take VP from here.
    Setup: place 2 VP on each Action Supply pile (per Wiki: 2 VP per Action
    Kingdom pile).
    """

    def __init__(self):
        super().__init__(
            name="Defiled Shrine",
            description=(
                "On gaining an Action, move 1 VP from its pile to here. "
                "On buying a Curse, take VP from here."
            ),
        )

    def setup(self, game_state) -> None:
        self.pile_vp = {}
        self.vp_pool = 0
        from dominion.cards.registry import get_card

        for name in game_state.supply:
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_action and not card.is_victory:
                self.pile_vp[name] = 2

    def on_gain(self, game_state, player, card) -> None:
        if card.is_action and self.pile_vp.get(card.name, 0) > 0:
            self.pile_vp[card.name] -= 1
            self.vp_pool += 1

    def on_buy(self, game_state, player, card) -> None:
        if card.name == "Curse":
            player.vp_tokens += self.vp_pool
            self.vp_pool = 0


class Fountain(Landmark):
    """At end of game, +15 VP if you have 10+ Coppers."""

    def __init__(self):
        super().__init__(
            name="Fountain",
            description="+15 VP at game end if 10+ Coppers.",
        )

    def vp_for(self, game_state, player) -> int:
        coppers = sum(1 for c in player.all_cards() if c.name == "Copper")
        return 15 if coppers >= 10 else 0


class Keep(Landmark):
    """At end of game, +5 VP per differently-named Treasure card you have a
    copy of more than (or tied with the most of) each other player.
    """

    def __init__(self):
        super().__init__(
            name="Keep",
            description="+5 VP per Treasure type you have most copies of.",
        )

    def vp_for(self, game_state, player) -> int:
        bonus = 0
        treasure_names = set()
        for p in game_state.players:
            for c in p.all_cards():
                if c.is_treasure:
                    treasure_names.add(c.name)
        for name in treasure_names:
            counts = [
                sum(1 for c in p.all_cards() if c.name == name)
                for p in game_state.players
            ]
            my_count = sum(1 for c in player.all_cards() if c.name == name)
            if my_count == 0:
                continue
            if my_count == max(counts):
                bonus += 5
        return bonus


class Labyrinth(Landmark):
    """When you gain a 2nd card on your turn, +2 VP from here.
    Setup: 6 VP per player."""

    def __init__(self):
        super().__init__(
            name="Labyrinth",
            description="When gaining your 2nd card of the turn, +2 VP.",
        )

    def setup(self, game_state) -> None:
        self.vp_pool = 6 * len(game_state.players)

    def on_gain(self, game_state, player, card) -> None:
        if self.vp_pool <= 0:
            return
        # cards_gained_this_turn was just incremented by gain_card; check ==2.
        if player.cards_gained_this_turn == 2:
            take = min(2, self.vp_pool)
            self.vp_pool -= take
            player.vp_tokens += take


class MountainPass(Landmark):
    """When the first player gains a Province, all bid; high bidder gains 8 VP
    and that much debt. Simplified: trigger fires once; the first Province
    gainer gets +8 VP and +8 debt (deterministic — caster usually wins bids).
    """

    def __init__(self):
        super().__init__(
            name="Mountain Pass",
            description="First Province gain triggers a debt-bid for 8 VP.",
        )
        self._fired = False

    def setup(self, game_state) -> None:
        self._fired = False

    def on_gain(self, game_state, player, card) -> None:
        if self._fired:
            return
        if card.name != "Province":
            return
        self._fired = True
        # Deterministic resolution: the gainer wins their own bid for the
        # maximum 40-debt, but per official rules max bid is 40. Default
        # behavior: gainer takes 8 VP and 8 debt (a sensible mid bid).
        player.vp_tokens += 8
        player.debt += 8


class Museum(Landmark):
    """At end of game, +2 VP per differently-named card you have."""

    def __init__(self):
        super().__init__(
            name="Museum",
            description="+2 VP per differently-named card.",
        )

    def vp_for(self, game_state, player) -> int:
        return 2 * len({c.name for c in player.all_cards()})


class Obelisk(Landmark):
    """Setup: choose an Action Supply pile. End: +2 VP per copy you have from that pile."""

    def __init__(self):
        super().__init__(
            name="Obelisk",
            description="+2 VP per copy of the chosen Action pile.",
        )

    def setup(self, game_state) -> None:
        from dominion.cards.registry import get_card

        # Pick the first Action pile in supply alphabetically (deterministic).
        candidates = []
        for name in game_state.supply:
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_action and not card.is_victory:
                candidates.append(name)
        candidates.sort()
        self.chosen_pile = candidates[0] if candidates else ""

    def vp_for(self, game_state, player) -> int:
        if not self.chosen_pile:
            return 0
        return 2 * sum(1 for c in player.all_cards() if c.name == self.chosen_pile)


class Orchard(Landmark):
    """+4 VP per differently-named Action card you have 3+ copies of."""

    def __init__(self):
        super().__init__(
            name="Orchard",
            description="+4 VP per Action with 3+ copies.",
        )

    def vp_for(self, game_state, player) -> int:
        counts: Counter = Counter()
        for c in player.all_cards():
            if c.is_action:
                counts[c.name] += 1
        return 4 * sum(1 for n, count in counts.items() if count >= 3)


class Palace(Landmark):
    """+3 VP per Copper-Silver-Gold set."""

    def __init__(self):
        super().__init__(
            name="Palace",
            description="+3 VP per Copper-Silver-Gold set.",
        )

    def vp_for(self, game_state, player) -> int:
        coppers = sum(1 for c in player.all_cards() if c.name == "Copper")
        silvers = sum(1 for c in player.all_cards() if c.name == "Silver")
        golds = sum(1 for c in player.all_cards() if c.name == "Gold")
        return 3 * min(coppers, silvers, golds)


class Tomb(Landmark):
    """When you trash a card, +1 VP."""

    def __init__(self):
        super().__init__(
            name="Tomb",
            description="When trashing a card, +1 VP.",
        )

    def on_trash(self, game_state, player, card) -> None:
        player.vp_tokens += 1


class Tower(Landmark):
    """+1 VP per non-Victory card you have from any empty Supply pile."""

    def __init__(self):
        super().__init__(
            name="Tower",
            description="+1 VP per non-Victory from each empty pile.",
        )

    def vp_for(self, game_state, player) -> int:
        empty = {name for name, count in game_state.supply.items() if count == 0}
        return sum(
            1
            for c in player.all_cards()
            if c.name in empty and not c.is_victory
        )


class TriumphalArch(Landmark):
    """+3 VP per copy of the second-most-played Action card."""

    def __init__(self):
        super().__init__(
            name="Triumphal Arch",
            description="+3 VP per copy of 2nd-most-common Action.",
        )

    def vp_for(self, game_state, player) -> int:
        counts: Counter = Counter()
        for c in player.all_cards():
            if c.is_action:
                counts[c.name] += 1
        if len(counts) < 2:
            return 0
        # Sort by descending count; second-most.
        sorted_counts = sorted(counts.values(), reverse=True)
        return 3 * sorted_counts[1]


class Wall(Landmark):
    """-1 VP per card you have over 15."""

    def __init__(self):
        super().__init__(
            name="Wall",
            description="-1 VP per card over 15.",
        )

    def vp_for(self, game_state, player) -> int:
        total = len(player.all_cards())
        return -max(0, total - 15)


class WolfDen(Landmark):
    """-3 VP per card you have exactly 1 copy of."""

    def __init__(self):
        super().__init__(
            name="Wolf Den",
            description="-3 VP per card with exactly 1 copy.",
        )

    def vp_for(self, game_state, player) -> int:
        counts: Counter = Counter()
        for c in player.all_cards():
            counts[c.name] += 1
        return -3 * sum(1 for v in counts.values() if v == 1)


ALL_LANDMARKS = [
    Aqueduct,
    Arena,
    BanditFort,
    Basilica,
    Battlefield,
    Colonnade,
    DefiledShrine,
    Fountain,
    Keep,
    Labyrinth,
    MountainPass,
    Museum,
    Obelisk,
    Orchard,
    Palace,
    Tomb,
    Tower,
    TriumphalArch,
    Wall,
    WolfDen,
]
