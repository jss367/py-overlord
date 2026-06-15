"""Board-derived island seeds for the island-model evolution pipeline.

The island model runs one GeneticTrainer per *seed* — each seed a distinct
theory of the kingdom — so the run escapes shared local optima. The original
pipeline hardcoded six hand-written Lisbon strategies, which meant a new
board required writing six seed strategies before islands could run at all.

This module derives the island roster from the board itself:

1. **Library reuse** — existing strategies whose referenced cards overlap
   this kingdom (:func:`find_compatible_strategies`), each as its own island.
2. **Trick seeds** — one island per mechanical interaction surfaced by the
   trick scanner (:func:`build_seed_genomes`).
3. **Big Money** — the archetype baseline island, always available.
4. **Random islands** — unseeded lineages (the structured-genome random init
   produces coherent menus, so these are real hypotheses, not noise) filling
   the roster up to ``max_islands``.

Island specs are plain dataclasses of strings: the pipeline runs each island
in a spawned subprocess, and strategy objects (lambda conditions) cannot be
serialized across that boundary. Workers rebuild the actual seed strategy
from the spec via :func:`resolve_island_seed`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from dominion.analysis.seed_genomes import build_seed_genomes
from dominion.analysis.strategy_library import find_compatible_strategies
from dominion.boards.loader import BoardConfig
from dominion.strategy.enhanced_strategy import EnhancedStrategy


@dataclass(frozen=True)
class IslandSpec:
    """A subprocess-safe description of one island's starting point.

    ``kind`` is one of ``"loader"`` (a registered strategy name), ``"library"``
    (a compatible strategy from the reuse library, keyed by entry name),
    ``"trick"`` (an index into ``build_seed_genomes(board)``), or ``"random"``
    (no seed — the island starts from random structured menus).
    """

    kind: str
    key: str
    name: str


def derive_island_specs(
    board: BoardConfig,
    max_islands: int = 6,
    reuse_top_k: int = 3,
    reuse_min_overlap: int = 2,
) -> list[IslandSpec]:
    """Derive an island roster for ``board``.

    Library and trick islands come first (they carry the most board-specific
    information), then the Big Money archetype, then random islands pad the
    roster to ``max_islands``. The Big Money archetype is *always* present in
    the returned roster (assuming ``max_islands >= 1``): it is the speed-test
    baseline every board should be measured against. When the informed islands
    (library + trick) alone would fill or overflow the roster, Big Money's slot
    is reserved — the informed specs are truncated to ``max_islands - 1`` and
    Big Money takes the final slot. Library entries are ranked by overlap score
    and trick seeds follow scanner order, so the cut keeps the strongest
    candidates while preserving their ranked order.
    """

    informed: list[IslandSpec] = []

    for entry in find_compatible_strategies(
        board.kingdom_cards, top_k=reuse_top_k, min_overlap=reuse_min_overlap
    ):
        informed.append(IslandSpec("library", entry.name, f"Reuse {entry.name}"))

    for index, (name, _strategy) in enumerate(build_seed_genomes(board)):
        informed.append(IslandSpec("trick", str(index), name))

    if max_islands <= 0:
        return []

    big_money = IslandSpec("loader", "Big Money", "Big Money Island")

    # Always reserve the final slot for the Big Money baseline. When the
    # informed specs would fill or overflow the roster, keep the strongest
    # ``max_islands - 1`` of them (ranked order preserved) and append Big Money.
    informed = informed[: max_islands - 1]
    specs: list[IslandSpec] = informed + [big_money]

    random_index = 0
    while len(specs) < max_islands:
        random_index += 1
        specs.append(IslandSpec("random", str(random_index), f"Random Island {random_index}"))

    return specs


def augment_panel_with_compatible(
    board: BoardConfig,
    baseline_names: list[str],
    strategy_loader,
    *,
    top_k: int = 3,
    min_overlap: int = 2,
) -> list[str]:
    """Build the default opponent panel: baselines + board-compatible strategies.

    The built-in baseline panel can collapse to just Big Money on boards whose
    kingdom excludes the engine opponents (e.g. Lisbon), making default runs
    silently weaker. The board-general fix is to fold in the board's compatible
    library strategies, so every board trains against a panel stronger than
    Big-Money-alone, derived from the board.

    Panel names are re-resolved by name (via ``StrategyLoader.get_strategy``) in
    both the island workers and ``scripts/island_merge.py``, so only names that
    round-trip through the loader are kept. Compatible library entries that are
    generated strategies the loader cannot resolve by name are skipped silently.
    Order is preserved (baselines first, then compatible) and names are deduped.
    """

    names: list[str] = list(baseline_names)
    seen = set(names)
    for entry in find_compatible_strategies(
        board.kingdom_cards, top_k=top_k, min_overlap=min_overlap
    ):
        if entry.name in seen:
            continue
        if strategy_loader.get_strategy(entry.name) is None:
            continue
        names.append(entry.name)
        seen.add(entry.name)
    return names


def resolve_island_seed(
    spec: IslandSpec,
    board: BoardConfig,
    strategy_loader,
) -> Optional[EnhancedStrategy]:
    """Rebuild the seed strategy for ``spec`` (inside the island subprocess).

    Returns ``None`` for ``"random"`` islands — the caller simply skips seed
    injection and lets the trainer start from random structured menus.
    Raises ``ValueError`` if a named seed can no longer be found, so a
    misconfigured island fails loudly instead of silently devolving into a
    random island with a misleading name.
    """

    if spec.kind == "random":
        return None

    if spec.kind == "loader":
        strategy = strategy_loader.get_strategy(spec.key)
        if strategy is None:
            raise ValueError(f"Island seed not found in strategy loader: {spec.key!r}")
        return strategy

    if spec.kind == "library":
        # The resolution lookup must be able to find any library spec that
        # ``derive_island_specs`` could have produced. derive selects with
        # ``top_k=reuse_top_k`` (the ``--reuse-top-k`` CLI flag is unbounded),
        # so a fixed bound here would silently miss specs ranked beyond it and
        # crash the island. Use an effectively-unbounded ``top_k`` so resolve's
        # candidate list is a superset of derive's, and keep ``min_overlap=1``
        # (always <= derive's ``reuse_min_overlap``, so the superset holds).
        entries = find_compatible_strategies(
            board.kingdom_cards, top_k=10_000, min_overlap=1
        )
        for entry in entries:
            if entry.name == spec.key:
                return entry.factory()
        raise ValueError(f"Island seed not found in strategy library: {spec.key!r}")

    if spec.kind == "trick":
        seeds = build_seed_genomes(board)
        index = int(spec.key)
        if index >= len(seeds):
            raise ValueError(
                f"Trick seed index {index} out of range ({len(seeds)} seeds on this board)"
            )
        return seeds[index][1]

    raise ValueError(f"Unknown island spec kind: {spec.kind!r}")
