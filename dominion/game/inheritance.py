"""Per-play dependencies for Estates sharing one physical Inheritance target."""

from collections import Counter
from dataclasses import dataclass, field

from dominion.cards.base_card import Card
from dominion.game.player_state import PlayerState


@dataclass(eq=False)
class InheritedPlay:
    player: PlayerState = field(repr=False)
    estate: Card
    instruction_source: Card
    duration_targets: list = field(default_factory=list)
    waiting: bool = False
    waiting_turn: tuple | None = None

    def __getattr__(self, name):
        source = self.__dict__.get("instruction_source")
        if source is None:
            raise AttributeError(name)
        return getattr(source, name)

    @property
    def virtual_supply_owner(self):
        return self.estate

    @property
    def waiting_for_gain(self):
        current = getattr(self.instruction_source, "_gain_turn", None)
        same_turn = self.waiting_turn is None or current is not None and (
            self.waiting_turn[:2] == current[:2] and self.waiting_turn[2] is current[2]
        )
        return self.waiting and same_turn and getattr(self.instruction_source, "waiting_for_gain", False)

    def set_aside_for_owner(self, player):
        source = self.instruction_source
        storage = getattr(source, "set_aside_for_owner", None)
        return storage(player) if storage else getattr(source, "set_aside", None)

    def snapshot(self):
        player = self.player
        reconcile_duration_owners(player)
        return (
            [Counter(player.duration), Counter(player.multiplied_durations)],
            Counter(play for plays in player.inherited_duration_plays.values() for play in plays),
        )

    def record(self, before):
        """Associate new source callbacks and nested dependencies with this play."""
        player, source = self.player, self.instruction_source
        for name, zone, prior in zip(
            ("duration", "multiplied_durations"),
            (player.duration, player.multiplied_durations), before[0],
        ):
            owners = player.inherited_duration_plays.setdefault((name, source), [])
            # Nested Estates may already have registered callbacks on this same
            # source. Do not claim their callbacks a second time.
            owners.extend([self] * max(0, zone.count(source) - len(owners)))
            for card in Counter(zone) - prior:
                if card is not source and card not in self.duration_targets:
                    self.duration_targets.append(card)
        after = Counter(play for plays in player.inherited_duration_plays.values() for play in plays)
        for play in after - before[1]:
            if play is not self and play not in self.duration_targets:
                self.duration_targets.append(play)
        for card in getattr(source, "duration_targets", []):
            if card is not source and card not in self.duration_targets:
                self.duration_targets.append(card)

    def on_cargo_ship_gain(self, state, player, gained):
        if not self.waiting_for_gain:
            return False
        before = self.snapshot()
        if not self.instruction_source.on_cargo_ship_gain(state, player, gained):
            return False
        self.waiting = False
        self.record(before)
        return True


def reconcile_duration_owners(player):
    """A resolved gain instruction may cancel its pending Duration directly."""
    for (name, source), owners in player.inherited_duration_plays.items():
        del owners[getattr(player, name).count(source):]
