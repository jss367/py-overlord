"""Render registered strategies as static HTML pages."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from html import escape
import inspect
from pathlib import Path
from shutil import copyfile
import textwrap
from typing import Iterable

from dominion.cards.base_card import CardType
from dominion.cards.registry import get_card
from dominion.simulation.strategy_battle import StrategyBattle
from dominion.reporting.strategy_links import PageLink, strategy_slug
from dominion.strategy.enhanced_strategy import EnhancedStrategy, PriorityRule, WayRule
from dominion.strategy.strategy_loader import StrategyLoader


@dataclass(frozen=True)
class RenderedStrategy:
    display_name: str
    slug: str
    strategy: EnhancedStrategy
    source_path: str
    factory_name: str
    references: dict[str, list[str]]
    compatible_boards: tuple[PageLink, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class CuratedStrategyGuide:
    """Metadata for a hand-authored guide that lives beside generated pages."""

    filename: str
    display_name: str
    description: str
    kingdom_cards: tuple[str, ...]
    source_label: str


CURATED_STRATEGY_GUIDES = (
    CuratedStrategyGuide(
        filename="cursed-band-biding-time-strategy-guide.html",
        display_name="Cursed Band and Biding Time Strategy Guide",
        description=(
            "Practical board guide: rush Cursed Band for Loot, activate Biding Time, "
            "manage Baths, and threaten a two-pile ending."
        ),
        kingdom_cards=(
            "Band of Misfits",
            "Experiment",
            "King's Cache",
            "Poet",
            "Trader",
        ),
        source_label="Repository simulation and card rules",
    ),
)

CURATED_STRATEGY_GUIDES_DIRECTORY = Path(__file__).with_name(
    "curated_strategy_guides"
)


def _tagged_condition_source(condition) -> str:
    """Return the explicit, serializable source attached to a condition."""

    if isinstance(condition, str):
        return condition
    return str(getattr(condition, "_source", ""))


def _callable_source(condition) -> str:
    """Recover readable source for a hand-written callable when possible."""

    if not callable(condition):
        return ""
    try:
        return textwrap.dedent(inspect.getsource(condition)).strip()
    except (OSError, TypeError):
        return ""


def _callable_expression(condition, source: str) -> ast.AST | None:
    """Extract a lambda or a single-return function's predicate expression."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None

    functions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if functions:
        if len(functions) == 1 and len(functions[0].body) == 1:
            statement = functions[0].body[0]
            if isinstance(statement, ast.Return):
                return statement.value
        return None

    lambdas = [node for node in ast.walk(tree) if isinstance(node, ast.Lambda)]
    if lambdas:
        return lambdas[0].body
    return None


def _closure_values(condition) -> dict[str, object]:
    if not callable(condition):
        return {}
    try:
        return inspect.getclosurevars(condition).nonlocals
    except TypeError:
        return {}


def _humanize_identifier(value: str) -> str:
    return value.strip("_").replace("_", " ").capitalize()


def _callable_condition_label(condition) -> str:
    """Derive a useful title from a custom condition's enclosing helper."""

    qualified_name = str(getattr(condition, "__qualname__", ""))
    parts = qualified_name.split(".<locals>.")
    candidate = parts[-2].split(".")[-1] if len(parts) > 1 else parts[-1].split(".")[-1]
    if candidate in {"condition", "_condition", "<lambda>", "__init__", ""}:
        return "Custom condition"

    label = _humanize_identifier(candidate)
    parameters = []
    for name, value in _closure_values(condition).items():
        if isinstance(value, (str, int, float, bool)):
            parameters.append(f"{name.strip('_').replace('_', ' ')}: {value}")
    if parameters:
        label += f" ({'; '.join(parameters)})"
    return label


def _condition_label(condition) -> str:
    if condition is None:
        return "Always"

    source = _tagged_condition_source(condition)
    if source:
        try:
            node = ast.parse(source, mode="eval").body
            try:
                return _humanize_condition_node(node)
            except (ValueError, TypeError):
                return _humanize_python_condition(node)
        except (SyntaxError, ValueError, TypeError):
            return source

    callable_source = _callable_source(condition)
    expression = _callable_expression(condition, callable_source)
    if expression is not None:
        try:
            return _humanize_python_condition(
                expression,
                values=_closure_values(condition),
            )
        except (ValueError, TypeError):
            pass
    return _callable_condition_label(condition)


_OPERATOR_LABELS = {
    "<": "less than",
    "<=": "at most",
    ">": "more than",
    ">=": "at least",
    "==": "exactly",
    "!=": "not",
}


def _call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    if isinstance(node.func, ast.Name):
        return node.func.id
    raise ValueError("Unsupported condition call")


def _literal_args(node: ast.Call) -> list[object]:
    return [ast.literal_eval(argument) for argument in node.args]


def _count_phrase(label: str, op: str, amount: int) -> str:
    return f"{label}: {_OPERATOR_LABELS.get(op, op)} {amount}"


def _card_list_phrase(cards: Iterable[str]) -> str:
    values = list(cards)
    if not values:
        return "the listed cards"
    if len(values) == 1:
        return values[0]
    return f"{', '.join(values[:-1])} or {values[-1]}"


def _humanize_condition_node(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id.strip("_").replace("_", " ").capitalize()
    if not isinstance(node, ast.Call):
        raise ValueError("Condition is not a call")

    name = _call_name(node)
    if name in {"and_", "or_"}:
        joiner = " and " if name == "and_" else " or "
        phrases = [
            _humanize_condition_node(argument)
            for argument in node.args
            if not (isinstance(argument, ast.Constant) and argument.value is None)
        ]
        return joiner.join(phrases)

    args = _literal_args(node)
    if name == "always_true":
        return "Always"
    if name == "provinces_left":
        return _count_phrase("Provinces remaining", str(args[0]), int(args[1]))
    if name == "colonies_left":
        return _count_phrase("Colonies remaining", str(args[0]), int(args[1]))
    if name == "turn_number":
        return _count_phrase("Turn number", str(args[0]), int(args[1]))
    if name == "resources":
        resources = {
            "actions": "Actions available",
            "buys": "Buys available",
            "coins": "Coins available",
            "potions": "Potions available",
            "hand_size": "Cards in hand",
        }
        label = resources.get(str(args[0]), str(args[0]).replace("_", " ").capitalize())
        return _count_phrase(label, str(args[1]), int(args[2]))
    if name == "has_cards":
        cards, amount = args
        label = _card_list_phrase(cards)
        if int(amount) <= 0:
            return f"You own no {label}"
        return f"You own at least {amount} total copies of {label}"
    if name == "has_no_cards":
        return f"You own no {_card_list_phrase(args[0])}"
    if name == "max_in_deck":
        card_name, amount = args
        if int(amount) == 1:
            return f"You do not own {card_name}"
        return f"You own fewer than {amount} copies of {card_name}"
    if name == "card_in_play":
        return f"{args[0]} is in play"
    if name == "card_in_hand":
        return f"{args[0]} is in hand"

    count_labels = {
        "actions_in_play": "Actions in play",
        "actions_gained_this_turn": "Actions gained this turn",
        "cards_gained_this_turn": "Cards gained this turn",
        "actions_in_hand": "Actions in hand",
        "terminals_in_hand": "Terminal Actions in hand",
        "treasures_in_hand": "Treasures in hand",
        "excess_actions": "Spare Actions",
        "empty_piles": "Empty Supply piles",
        "deck_size": "Deck size",
        "score_diff": "Victory-point lead",
    }
    if name in count_labels:
        return _count_phrase(count_labels[name], str(args[0]), int(args[1]))
    if name == "pile_count":
        return _count_phrase(f"{args[0]} cards remaining", str(args[1]), int(args[2]))
    if name == "action_density":
        return f"Action density is {_OPERATOR_LABELS.get(str(args[0]), args[0])} {args[1]}%"
    if name == "deck_count_diff":
        return _count_phrase(
            f"{args[0]} count minus {args[1]} count",
            str(args[2]),
            int(args[3]),
        )
    raise ValueError(f"Unknown condition helper: {name}")


_COMPARISON_LABELS = {
    ast.Lt: "less than",
    ast.LtE: "at most",
    ast.Gt: "more than",
    ast.GtE: "at least",
    ast.Eq: "exactly",
    ast.NotEq: "not",
    ast.Is: "is",
    ast.IsNot: "is not",
    ast.In: "is among",
    ast.NotIn: "is not among",
}


def _resolved_value(node: ast.AST, values: dict[str, object]) -> object:
    if isinstance(node, ast.Name) and node.id in values:
        return values[node.id]
    return ast.literal_eval(node)


def _call_argument(node: ast.Call, index: int, values: dict[str, object]) -> object:
    return _resolved_value(node.args[index], values)


def _deck_count_card(node: ast.AST, values: dict[str, object]) -> str | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    if node.func.attr not in {"count_in_deck", "count"} or not node.args:
        return None
    try:
        return str(_call_argument(node, 0, values))
    except (ValueError, TypeError):
        if isinstance(node.args[0], ast.Name):
            return node.args[0].id
        return None


def _supply_count_card(node: ast.AST, values: dict[str, object]) -> str | None:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return None
    owner = node.func.value
    if (
        node.func.attr != "get"
        or not isinstance(owner, ast.Attribute)
        or owner.attr != "supply"
        or not node.args
    ):
        return None
    try:
        return str(_call_argument(node, 0, values))
    except (ValueError, TypeError):
        return None


def _remaining_pile_label(card_name: str) -> str:
    plurals = {"Colony": "Colonies", "Duchy": "Duchies", "Province": "Provinces"}
    return f"{plurals.get(card_name, card_name + ' cards')} remaining"


def _humanize_python_value(node: ast.AST, values: dict[str, object]) -> str:
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Name):
        if node.id in values and isinstance(values[node.id], (str, int, float, bool)):
            return str(values[node.id])
        return _humanize_identifier(node.id)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return _card_list_phrase(
            _humanize_python_value(item, values) for item in node.elts
        )
    if isinstance(node, ast.Attribute):
        attributes = {
            "turn_number": "Turn number",
            "provinces_left": "Provinces remaining",
            "colonies_left": "Colonies remaining",
            "actions": "Actions available",
            "buys": "Buys available",
            "coins": "Coins available",
            "potions": "Potions available",
            "hand": "Cards in hand",
            "in_play": "Cards in play",
        }
        return attributes.get(node.attr, _humanize_identifier(node.attr))
    if isinstance(node, ast.Call):
        deck_card = _deck_count_card(node, values)
        if deck_card is not None:
            return f"{deck_card} copies owned"

        supply_card = _supply_count_card(node, values)
        if supply_card is not None:
            return _remaining_pile_label(supply_card)

        name = _call_name(node)
        if name == "len" and node.args:
            return _humanize_python_value(node.args[0], values)
        if name == "get_card" and node.args:
            return _humanize_python_value(node.args[0], values)
        if name == "get_card_cost" and len(node.args) >= 2:
            return f"{_humanize_python_value(node.args[1], values)} cost"
        if name == "any" and node.args and isinstance(node.args[0], ast.GeneratorExp):
            generator = node.args[0]
            if generator.generators:
                source = generator.generators[0].iter
                comparison = generator.elt
                if (
                    isinstance(source, ast.Attribute)
                    and source.attr == "in_play"
                    and isinstance(comparison, ast.Compare)
                    and len(comparison.comparators) == 1
                ):
                    return f"{_humanize_python_value(comparison.comparators[0], values)} is in play"
        arguments = ", ".join(_humanize_python_value(arg, values) for arg in node.args)
        return f"{_humanize_identifier(name)}({arguments})"
    if isinstance(node, ast.BinOp):
        operators = {
            ast.Add: "plus",
            ast.Sub: "minus",
            ast.Mult: "times",
            ast.Div: "divided by",
        }
        operator = operators.get(type(node.op), ast.unparse(node.op))
        return (
            f"{_humanize_python_value(node.left, values)} {operator} "
            f"{_humanize_python_value(node.right, values)}"
        )
    return ast.unparse(node)


def _humanize_python_condition(
    node: ast.AST,
    *,
    values: dict[str, object] | None = None,
) -> str:
    """Translate common hand-written predicates without executing them."""

    values = values or {}
    if isinstance(node, ast.BoolOp):
        joiner = " and " if isinstance(node.op, ast.And) else " or "
        return joiner.join(
            _humanize_python_condition(value, values=values) for value in node.values
        )
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return f"not ({_humanize_python_condition(node.operand, values=values)})"
    if (
        isinstance(node, ast.Call)
        and _call_name(node) == "cmp"
        and len(node.args) == 2
        and values.get("cmp") is not None
    ):
        comparison_type = next(
            (
                {
                    "<": ast.Lt,
                    "<=": ast.LtE,
                    ">": ast.Gt,
                    ">=": ast.GtE,
                    "==": ast.Eq,
                    "!=": ast.NotEq,
                }[symbol]
                for symbol, comparator in PriorityRule._OP_MAP.items()
                if comparator is values["cmp"]
            ),
            None,
        )
        if comparison_type is not None:
            return _humanize_python_condition(
                ast.Compare(
                    left=node.args[0],
                    ops=[comparison_type()],
                    comparators=[node.args[1]],
                ),
                values=values,
            )
    if isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1:
        operator = _COMPARISON_LABELS.get(type(node.ops[0]), ast.unparse(node.ops[0]))
        right_node = node.comparators[0]
        left_card = _deck_count_card(node.left, values)
        try:
            right_value = _resolved_value(right_node, values)
        except (ValueError, TypeError):
            right_value = None

        if left_card is not None and isinstance(right_value, (int, float)):
            if isinstance(node.ops[0], ast.Eq) and right_value == 0:
                return f"You own no {left_card}"
            if isinstance(node.ops[0], ast.Lt) and right_value == 1:
                return f"You do not own {left_card}"
            if isinstance(node.ops[0], ast.Gt) and right_value == 0:
                return f"You own {left_card}"
            if isinstance(node.ops[0], ast.Lt):
                return f"You own fewer than {right_value} copies of {left_card}"
            if isinstance(node.ops[0], ast.LtE):
                noun = "copy" if right_value == 1 else "copies"
                return f"You own at most {right_value} {noun} of {left_card}"
            if isinstance(node.ops[0], ast.GtE):
                noun = "copy" if right_value == 1 else "copies"
                return f"You own at least {right_value} {noun} of {left_card}"
            if isinstance(node.ops[0], ast.Gt):
                noun = "copy" if right_value == 1 else "copies"
                return f"You own more than {right_value} {noun} of {left_card}"

        left = _humanize_python_value(node.left, values)
        right = _humanize_python_value(right_node, values)
        return f"{left}: {operator} {right}"
    if isinstance(node, ast.Call):
        return _humanize_python_value(node, values)
    return ast.unparse(node)


def _condition_detail(condition) -> str:
    source = _tagged_condition_source(condition)
    if source:
        return source

    source = _callable_source(condition)
    expression = _callable_expression(condition, source)
    if expression is not None:
        source = ast.unparse(expression)

    parameters = [
        f"{name} = {value!r}"
        for name, value in _closure_values(condition).items()
        if isinstance(value, (str, int, float, bool))
    ]
    if parameters:
        source = f"{source}\n\nConfigured values: {', '.join(parameters)}"
    return source or "Source unavailable"


def _condition_markup(condition) -> str:
    label = escape(_condition_label(condition))
    if condition is None:
        return f'<span class="condition condition-always">{label}</span>'
    source = _condition_detail(condition)
    return (
        '<details class="condition-detail">'
        f'<summary><span class="condition">{label}</span></summary>'
        f"<pre><code>{escape(source)}</code></pre>"
        "</details>"
    )


_PRIMARY_CARD_TYPES = (
    CardType.CURSE,
    CardType.VICTORY,
    CardType.TREASURE,
    CardType.NIGHT,
    CardType.ACTION,
)


def _card_chip(name: str) -> str:
    """Render a card using the types from the canonical card registry."""

    try:
        card = get_card(name)
    except (KeyError, ValueError):
        return f'<span class="card-chip card-unknown">{escape(name)}</span>'

    primary = next(
        (card_type for card_type in _PRIMARY_CARD_TYPES if card_type in card.types),
        None,
    )
    primary_name = primary.value if primary is not None else "other"
    type_names = [card_type.value for card_type in card.types]
    modifier_types = [
        card_type
        for card_type in card.types
        if card_type is not primary
        and card_type
        in {
            CardType.ATTACK,
            CardType.REACTION,
            CardType.DURATION,
            CardType.RESERVE,
            CardType.TRAVELLER,
            CardType.LIAISON,
            CardType.OMEN,
            CardType.ACTION,
            CardType.TREASURE,
            CardType.VICTORY,
            CardType.CURSE,
            CardType.NIGHT,
        }
    ]
    markers = "".join(
        f'<span class="type-marker marker-{card_type.value}" title="{card_type.value.title()}" aria-hidden="true"></span>'
        for card_type in modifier_types
    )
    special = (
        f" card-{card.name.lower()}"
        if card.name in {"Copper", "Silver", "Gold"}
        else ""
    )
    type_label = ", ".join(value.title() for value in type_names) or "Card"
    return (
        f'<span class="card-chip type-{primary_name}{special}" '
        f'aria-label="{escape(card.name)}, {escape(type_label)} card">'
        f"<span>{escape(card.name)}</span>{markers}</span>"
    )


def _landscape_chip(name: str, kind: str) -> str:
    css_kind = {
        "Allies": "ally",
        "Prophecies": "prophecy",
    }.get(kind, kind.lower().rstrip("s").replace(" ", "-"))
    return f'<span class="landscape-chip landscape-{css_kind}">{escape(name)}</span>'


def _typed_value_list(values: Iterable[str], kind: str) -> str:
    items = list(values)
    if not items:
        return '<span class="empty">None</span>'
    if kind == "Kingdom Cards":
        return (
            '<span class="chip-list">'
            + "".join(_card_chip(value) for value in items)
            + "</span>"
        )
    return (
        '<span class="chip-list">'
        + "".join(_landscape_chip(value, kind) for value in items)
        + "</span>"
    )


def _priority_target_chip(
    name: str,
    landscape_references: dict[str, list[str]] | None = None,
) -> str:
    if landscape_references:
        for kind in ("Events", "Projects", "Ways", "Landmarks", "Allies"):
            if name in landscape_references.get(kind, []):
                return _landscape_chip(name, kind)
    return _card_chip(name)


def _priority_rows(
    rules: Iterable[PriorityRule],
    *,
    landscape_references: dict[str, list[str]] | None = None,
) -> str:
    rows = []
    for index, rule in enumerate(rules, 1):
        rows.append(
            "<tr>"
            f'<td data-label="Priority"><span class="priority-number">{index}</span></td>'
            f'<td data-label="Card">{_priority_target_chip(rule.card_name, landscape_references)}</td>'
            f'<td data-label="Condition">{_condition_markup(rule.condition)}</td>'
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="3" class="empty">None</td></tr>'
    return "\n".join(rows)


def _way_rows(rules: Iterable[WayRule]) -> str:
    rows = []
    for index, rule in enumerate(rules, 1):
        rows.append(
            "<tr>"
            f'<td data-label="Priority"><span class="priority-number">{index}</span></td>'
            f'<td data-label="Card">{_card_chip(rule.card_name)}</td>'
            f'<td data-label="Way">{_landscape_chip(rule.way_name, "Ways")}</td>'
            f'<td data-label="Condition">{_condition_markup(rule.condition)}</td>'
            "</tr>"
        )
    if not rows:
        return '<tr><td colspan="4" class="empty">None</td></tr>'
    return "\n".join(rows)


def _reference_list(values: list[str], kind: str = "Kingdom Cards") -> str:
    return _typed_value_list(values, kind)


def _page_link_list(values: Iterable[PageLink]) -> str:
    links = list(values)
    if not links:
        return '<span class="empty">None</span>'
    return (
        '<span class="chip-list">'
        + "".join(
            f'<a class="board-chip" href="{escape(link.href)}">{escape(link.label)}</a>'
            for link in links
        )
        + "</span>"
    )


def _strategy_source(loader: StrategyLoader, display_name: str) -> tuple[str, str]:
    factory = loader.strategies.get(display_name)
    if factory is None:
        factory = loader.strategies.get(display_name.lower())
    if factory is None:
        return "", ""

    source = inspect.getsourcefile(factory) or ""
    try:
        source = str(Path(source).resolve().relative_to(Path.cwd()))
    except ValueError:
        source = str(Path(source).resolve()) if source else ""
    return source, getattr(factory, "__name__", "")


def _strategy_tags(item: RenderedStrategy) -> list[str]:
    """Return conservative labels supported by the strategy's own metadata."""

    strategy = item.strategy
    searchable = f"{item.display_name} {getattr(strategy, 'description', '')}".lower()
    labels = []
    for needle, label in (
        ("big money", "Big Money"),
        ("engine", "Engine"),
        ("rush", "Rush"),
        ("slog", "Slog"),
        ("rebuild", "Rebuild"),
    ):
        if needle in searchable:
            labels.append(label)
    if getattr(strategy, "way_policy", None):
        labels.append("Way policy")
    return labels


def _audience_description(strategy: EnhancedStrategy) -> str:
    """Expand terse strategy-writing conventions in visible summaries."""

    description = getattr(strategy, "description", "") or "No description provided."
    replacements = (
        ("alt-VP", "alternate victory points"),
        (" VP", " victory points"),
        ("5T/4I", "five Torturers / four Inns"),
        ("actions>1", "more than one Action remains"),
    )
    for shorthand, expanded in replacements:
        description = description.replace(shorthand, expanded)
    return description


def _tags_markup(labels: Iterable[str]) -> str:
    values = list(dict.fromkeys(labels))
    if not values:
        return ""
    return (
        '<span class="tags">'
        + "".join(f'<span class="tag">{escape(label)}</span>' for label in values)
        + "</span>"
    )


def collect_rendered_strategies(
    loader: StrategyLoader | None = None,
    *,
    names: Iterable[str] | None = None,
) -> list[RenderedStrategy]:
    """Instantiate registered strategies and collect metadata for rendering."""

    loader = loader or StrategyLoader()
    battle = StrategyBattle(log_frequency=0)
    display_names = list(names) if names is not None else loader.list_strategies()
    rendered = []

    for display_name in sorted(display_names):
        strategy = loader.get_strategy(display_name)
        if strategy is None:
            raise ValueError(f"Unknown strategy: {display_name}")

        resolved_name = loader.get_display_name(display_name) or display_name
        refs = battle._split_board_references(
            battle._extract_cards_from_strategy(strategy)
        )
        source_path, factory_name = _strategy_source(loader, resolved_name)
        rendered.append(
            RenderedStrategy(
                display_name=resolved_name,
                slug=strategy_slug(resolved_name),
                strategy=strategy,
                source_path=source_path,
                factory_name=factory_name,
                references={
                    "Kingdom Cards": refs.kingdom_cards,
                    "Events": refs.events,
                    "Projects": refs.projects,
                    "Ways": refs.ways,
                    "Landmarks": refs.landmarks,
                    "Allies": refs.allies,
                },
            )
        )

    return rendered


def _page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --canvas: #f4f0e6;
      --surface: #fffdf8;
      --surface-raised: #ffffff;
      --border: #d9d0bd;
      --border-strong: #b7aa91;
      --text: #28231d;
      --muted: #72695d;
      --accent: #245f73;
      --accent-dark: #174555;
      --shadow: 0 12px 30px rgb(64 48 28 / 8%);
      --action: #f3ebdd;
      --treasure: #e8c65a;
      --victory: #83b96c;
      --curse: #9270ac;
      --reaction: #5b8fc4;
      --attack: #b85d55;
      --duration: #de914a;
      --night: #45434a;
    }}
    * {{ box-sizing: border-box; }}
    [hidden] {{ display: none !important; }}
    body {{
      background:
        radial-gradient(circle at top left, rgb(232 198 90 / 12%), transparent 28rem),
        var(--canvas);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
      margin: 0 auto;
      max-width: 1180px;
      min-height: 100vh;
      padding: 28px 28px 64px;
    }}
    a {{ color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 2px; }}
    a:hover {{ color: var(--accent-dark); }}
    h1, h2 {{ font-family: Georgia, "Times New Roman", serif; }}
    h1 {{ font-size: clamp(2.15rem, 5vw, 3.45rem); letter-spacing: -.035em; line-height: 1.05; margin: 0; }}
    h2 {{ font-size: 1.45rem; margin: 0; }}
    p {{ margin: .6rem 0; }}
    nav {{ align-items: center; display: flex; gap: 16px; margin-bottom: 18px; }}
    nav a, .back-link {{ font-size: .9rem; font-weight: 700; text-decoration: none; }}
    nav a::before, .back-link::before {{ content: "← "; }}
    .muted, .empty {{ color: var(--muted); }}
    .eyebrow {{ color: var(--accent); font-size: .72rem; font-weight: 800; letter-spacing: .14em; margin-bottom: 8px; text-transform: uppercase; }}
    .hero {{
      background: linear-gradient(135deg, rgb(255 255 255 / 92%), rgb(255 253 248 / 86%));
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 26px;
      overflow: hidden;
      padding: clamp(24px, 5vw, 44px);
      position: relative;
    }}
    .hero::after {{
      background: linear-gradient(180deg, var(--treasure), #b98a27);
      content: "";
      inset: 0 0 0 auto;
      position: absolute;
      width: 6px;
    }}
    .hero-description {{ color: #51483e; font-size: 1.05rem; margin: 14px 0 0; max-width: 760px; }}
    .hero-links {{ align-items: center; display: flex; flex-wrap: wrap; gap: 10px 14px; margin-top: 20px; }}
    .hero-links strong {{ color: var(--muted); font-size: .76rem; letter-spacing: .06em; text-transform: uppercase; }}
    .section {{ margin-top: 30px; }}
    .section-heading {{ align-items: center; display: flex; gap: 10px; margin-bottom: 10px; }}
    .section-icon {{
      align-items: center;
      background: var(--section-color, var(--accent));
      border-radius: 9px;
      color: #fff;
      display: inline-flex;
      font-size: .9rem;
      font-weight: 900;
      height: 30px;
      justify-content: center;
      width: 30px;
    }}
    .section-gain {{ --section-color: #5f9251; }}
    .section-action {{ --section-color: #9b815a; }}
    .section-trash {{ --section-color: #a65b54; }}
    .section-treasure {{ --section-color: #bd8c24; }}
    .section-way {{ --section-color: #518ea6; }}
    .meta {{
      display: grid;
      gap: 12px 24px;
      grid-template-columns: minmax(120px, max-content) 1fr;
      margin: 16px 0 0;
    }}
    .meta dt {{ color: var(--muted); font-size: .75rem; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; }}
    .meta dd {{ margin: 0; min-width: 0; overflow-wrap: anywhere; }}
    .technical-details {{
      background: rgb(255 255 255 / 55%);
      border: 1px solid var(--border);
      border-radius: 12px;
      margin-top: 18px;
      padding: 0 16px;
    }}
    .technical-details > summary {{ color: var(--muted); cursor: pointer; font-size: .86rem; font-weight: 750; padding: 12px 0; }}
    .technical-details[open] > summary {{ border-bottom: 1px solid var(--border); }}
    .technical-details .meta {{ padding-bottom: 16px; }}
    table {{
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-collapse: separate;
      border-radius: 12px;
      border-spacing: 0;
      box-shadow: 0 4px 14px rgb(64 48 28 / 5%);
      margin: 0;
      overflow: hidden;
      width: 100%;
    }}
    th, td {{
      border-bottom: 1px solid #e8e1d4;
      padding: 11px 14px;
      text-align: left;
      vertical-align: middle;
    }}
    th {{ background: #eee8dc; color: #675d50; font-size: .71rem; letter-spacing: .07em; position: sticky; text-transform: uppercase; top: 0; }}
    tr:last-child td {{ border-bottom: 0; }}
    tbody tr:hover td, table tr:not(:first-child):hover td {{ background: #fffcf4; }}
    td:first-child {{ width: 68px; }}
    .priority-number {{
      align-items: center;
      background: var(--section-color, var(--accent));
      border-radius: 50%;
      color: #fff;
      display: inline-flex;
      font-size: .78rem;
      font-weight: 800;
      height: 27px;
      justify-content: center;
      width: 27px;
    }}
    .chip-list {{ align-items: center; display: flex; flex-wrap: wrap; gap: 7px; }}
    .card-chip, .landscape-chip, .board-chip, .strategy-link-chip, .tag {{
      align-items: center;
      border: 1px solid rgb(48 41 31 / 22%);
      border-radius: 999px;
      color: #28231d;
      display: inline-flex;
      font-size: .8rem;
      font-weight: 750;
      gap: 5px;
      line-height: 1.1;
      min-height: 27px;
      padding: 5px 10px;
      text-decoration: none;
      white-space: nowrap;
    }}
    .card-chip.type-action {{ background: var(--action); }}
    .card-chip.type-treasure {{ background: var(--treasure); }}
    .card-chip.type-victory {{ background: var(--victory); }}
    .card-chip.type-curse {{ background: var(--curse); color: #fff; }}
    .card-chip.type-night {{ background: var(--night); color: #fff; }}
    .card-chip.type-other, .card-chip.card-unknown {{ background: #e9e4da; }}
    .card-chip.card-copper {{ background: #c88758; }}
    .card-chip.card-silver {{ background: #d8dcdf; }}
    .card-chip.card-gold {{ background: #e7bd42; }}
    .type-marker {{ border: 1px solid rgb(0 0 0 / 22%); border-radius: 50%; height: 8px; width: 8px; }}
    .marker-attack {{ background: var(--attack); }}
    .marker-reaction {{ background: var(--reaction); }}
    .marker-duration {{ background: var(--duration); }}
    .marker-action {{ background: var(--action); }}
    .marker-treasure {{ background: var(--treasure); }}
    .marker-victory {{ background: var(--victory); }}
    .marker-curse {{ background: var(--curse); }}
    .marker-night {{ background: var(--night); }}
    .marker-reserve, .marker-traveller {{ background: #b89563; }}
    .marker-liaison {{ background: #8a72a7; }}
    .marker-omen {{ background: #6a94a2; }}
    .landscape-chip {{ border-radius: 7px; }}
    .landscape-event {{ background: #dedbd3; }}
    .landscape-project {{ background: #e6a99f; }}
    .landscape-way {{ background: #9dc8d7; }}
    .landscape-landmark {{ background: #8caf72; }}
    .landscape-ally {{ background: #ddc99a; }}
    .landscape-trait {{ background: #c8b08c; }}
    .landscape-prophecy {{ background: #a8c9cf; }}
    .board-chip {{ background: #e8f0ef; border-color: #b4cbc7; color: #245f73; }}
    .board-chip::before {{ content: "▦"; font-size: .72rem; }}
    .strategy-link-chip {{ background: #f0eadc; border-color: #d6c7a9; color: #6b5327; }}
    .strategy-link-chip::before {{ content: "♟"; font-size: .72rem; }}
    .coin-badge {{
      align-items: center;
      background: var(--treasure);
      border: 2px solid #9d7620;
      border-radius: 50%;
      box-shadow: inset 0 0 0 2px rgb(255 255 255 / 38%);
      display: inline-flex;
      font-size: .78rem;
      font-weight: 900;
      height: 29px;
      justify-content: center;
      width: 29px;
    }}
    .condition {{
      background: #edf1f2;
      border: 1px solid #d3dfe1;
      border-radius: 999px;
      color: #334e57;
      display: inline-block;
      font-size: .79rem;
      font-weight: 650;
      line-height: 1.25;
      padding: 5px 9px;
    }}
    .condition-always {{ background: #f2efe9; border-color: #ded7ca; color: var(--muted); }}
    .condition-detail summary {{ cursor: pointer; list-style-position: outside; }}
    .condition-detail summary::marker {{ color: #8da1a7; font-size: .72rem; }}
    .condition-detail pre {{ margin: 7px 0 0; max-width: 720px; }}
    .condition-detail code {{ background: #282b2d; border-radius: 7px; color: #f3eee4; display: block; font-size: .73rem; overflow-wrap: anywhere; padding: 8px 10px; white-space: pre-wrap; }}
    .search {{
      background: var(--surface-raised);
      border: 1px solid var(--border-strong);
      border-radius: 999px;
      box-shadow: 0 3px 10px rgb(64 48 28 / 5%);
      color: var(--text);
      font: inherit;
      margin: 20px 0 22px;
      padding: 11px 16px;
      width: min(520px, 100%);
    }}
    .search:focus {{ border-color: var(--accent); outline: 3px solid rgb(36 95 115 / 15%); }}
    .catalog-grid {{ display: grid; gap: 14px; grid-template-columns: repeat(auto-fill, minmax(min(330px, 100%), 1fr)); }}
    .strategy-card, .board-card {{
      background: var(--surface-raised);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: 0 5px 16px rgb(64 48 28 / 5%);
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 0;
      padding: 20px;
      transition: border-color .15s ease, transform .15s ease, box-shadow .15s ease;
    }}
    .strategy-card:hover, .board-card:hover {{ border-color: var(--border-strong); box-shadow: var(--shadow); transform: translateY(-2px); }}
    .strategy-card h2, .board-card h2 {{ font-size: 1.22rem; line-height: 1.2; }}
    .strategy-card h2 a, .board-card h2 a {{ color: var(--text); text-decoration: none; }}
    .strategy-card p, .board-card p {{ color: #5d554a; font-size: .88rem; margin: 0; }}
    .card-footer {{ align-items: center; border-top: 1px solid #ece5d9; color: var(--muted); display: flex; flex-wrap: wrap; font-size: .75rem; gap: 8px 14px; margin-top: auto; padding-top: 12px; }}
    .tags {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tag {{ background: #f0ede6; border: 0; color: #655c50; font-size: .68rem; letter-spacing: .04em; min-height: 22px; padding: 4px 8px; text-transform: uppercase; }}
    .empty-state {{ background: rgb(255 255 255 / 55%); border: 1px dashed var(--border-strong); border-radius: 12px; color: var(--muted); padding: 18px; }}
    @media (max-width: 680px) {{
      body {{ padding: 18px 14px 44px; }}
      .hero {{ border-radius: 14px; }}
      .meta {{ grid-template-columns: 1fr; gap: 3px; }}
      .meta dd + dt {{ margin-top: 9px; }}
      .priority-table {{ background: transparent; border: 0; box-shadow: none; overflow: visible; }}
      .priority-table thead {{ clip: rect(0 0 0 0); clip-path: inset(50%); height: 1px; overflow: hidden; position: absolute; white-space: nowrap; width: 1px; }}
      .priority-table tbody, .priority-table tr, .priority-table td {{ display: block; width: 100%; }}
      .priority-table tr {{ background: var(--surface-raised); border: 1px solid var(--border); border-radius: 11px; box-shadow: 0 3px 10px rgb(64 48 28 / 5%); margin-bottom: 10px; overflow: hidden; padding: 9px 12px; }}
      .priority-table td {{ border: 0; padding: 6px 0 6px 92px; position: relative; }}
      .priority-table td::before {{ color: var(--muted); content: attr(data-label); font-size: .68rem; font-weight: 800; left: 0; letter-spacing: .05em; position: absolute; text-transform: uppercase; top: 9px; }}
      .priority-table td[colspan] {{ padding-left: 0; text-align: center; }}
      .priority-table td[colspan]::before {{ content: none; }}
    }}
    @media print {{
      body {{ background: #fff; max-width: none; padding: 0; }}
      .hero, table, .strategy-card, .board-card {{ box-shadow: none; }}
      .search, script {{ display: none; }}
      .condition-detail code {{ color: #000; background: #eee; }}
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def render_strategy_page(
    item: RenderedStrategy, *, index_href: str = "index.html"
) -> str:
    strategy = item.strategy
    references = "".join(
        f"<dt>{escape(label)}</dt><dd>{_reference_list(values, label)}</dd>"
        for label, values in item.references.items()
    )
    body = f"""
<nav><a href="{escape(index_href)}">Strategy index</a></nav>
<header class="hero">
  <p class="eyebrow">Dominion strategy</p>
  <h1>{escape(item.display_name)}</h1>
  <p class="hero-description">{escape(_audience_description(strategy))}</p>
{_tags_markup(_strategy_tags(item))}
  <div class="hero-links"><strong>Compatible boards</strong>{_page_link_list(item.compatible_boards)}</div>
  <details class="technical-details">
    <summary>Implementation details and referenced components</summary>
    <dl class="meta">
      <dt>Internal name</dt><dd>{escape(getattr(strategy, "name", ""))}</dd>
      <dt>Version</dt><dd>{escape(getattr(strategy, "version", ""))}</dd>
      <dt>Source</dt><dd>{escape(item.source_path or "Unknown")}</dd>
      <dt>Factory</dt><dd>{escape(item.factory_name or "Unknown")}</dd>
      {references}
    </dl>
  </details>
</header>

<section class="section section-gain">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">↓</span><h2>Gain Priority</h2></div>
  <table class="priority-table">
    <thead><tr><th>#</th><th>Card or Event</th><th>Condition</th></tr></thead>
    <tbody>{_priority_rows(getattr(strategy, "gain_priority", []), landscape_references=item.references)}</tbody>
  </table>
</section>

<section class="section section-action">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">A</span><h2>Action Priority</h2></div>
  <table class="priority-table">
    <thead><tr><th>#</th><th>Card</th><th>Condition</th></tr></thead>
    <tbody>{_priority_rows(getattr(strategy, "action_priority", []))}</tbody>
  </table>
</section>

<section class="section section-trash">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">×</span><h2>Trash Priority</h2></div>
  <table class="priority-table">
    <thead><tr><th>#</th><th>Card</th><th>Condition</th></tr></thead>
    <tbody>{_priority_rows(getattr(strategy, "trash_priority", []))}</tbody>
  </table>
</section>

<section class="section section-treasure">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">$</span><h2>Treasure Priority</h2></div>
  <table class="priority-table">
    <thead><tr><th>#</th><th>Card</th><th>Condition</th></tr></thead>
    <tbody>{_priority_rows(getattr(strategy, "treasure_priority", []))}</tbody>
  </table>
</section>

<section class="section section-way">
  <div class="section-heading"><span class="section-icon" aria-hidden="true">W</span><h2>Way Policy</h2></div>
  <table class="priority-table">
    <thead><tr><th>#</th><th>Card</th><th>Way</th><th>Condition</th></tr></thead>
    <tbody>{_way_rows(getattr(strategy, "way_policy", []) or [])}</tbody>
  </table>
</section>
"""
    return _page_shell(f"{item.display_name} Strategy", body)


def render_strategy_index(
    items: list[RenderedStrategy],
    *,
    curated_guides: Iterable[CuratedStrategyGuide] = (),
    board_index_href: str | None = None,
) -> str:
    rows = []
    for guide in curated_guides:
        rows.append(
            '<article class="strategy-card strategy-row">'
            f'<h2><a href="{escape(guide.filename)}">{escape(guide.display_name)}</a></h2>'
            f"<p>{escape(guide.description)}</p>"
            f'{_tags_markup(["Curated guide"])}'
            f'<div class="chip-list">{"".join(_card_chip(card) for card in guide.kingdom_cards)}</div>'
            '<div class="card-footer">'
            f"<span>{len(guide.kingdom_cards)} referenced cards</span>"
            f"<span>{escape(guide.source_label)}</span>"
            "</div>"
            "</article>"
        )

    for item in items:
        strategy = item.strategy
        refs = item.references["Kingdom Cards"]
        rows.append(
            '<article class="strategy-card strategy-row">'
            f'<h2><a href="{escape(item.slug)}.html">{escape(item.display_name)}</a></h2>'
            f"<p>{escape(_audience_description(strategy))}</p>"
            f"{_tags_markup(_strategy_tags(item))}"
            f'<div class="chip-list">{"".join(_card_chip(card) for card in refs)}</div>'
            '<div class="card-footer">'
            f"<span>{len(refs)} referenced card{'s' if len(refs) != 1 else ''}</span>"
            f"<span>{len(item.compatible_boards)} compatible board{'s' if len(item.compatible_boards) != 1 else ''}</span>"
            "</div>"
            "</article>"
        )

    board_nav = (
        f'<nav><a href="{escape(board_index_href)}">Board index</a></nav>'
        if board_index_href
        else ""
    )
    body = f"""
{board_nav}
<header class="hero">
  <p class="eyebrow">Dominion simulator</p>
  <h1>Strategy Index</h1>
  <p class="hero-description">Browse registered strategies and curated board guides, their defining cards, and the boards they support.</p>
</header>
<label for="strategy-search" class="eyebrow">Find a strategy</label><br>
<input class="search" id="strategy-search" type="search" placeholder="Search by name, description, card, or style">
<div class="catalog-grid" id="strategy-grid">
  {"".join(rows)}
</div>
<p class="empty-state" id="strategy-empty" hidden>No strategies match that search.</p>
<script>
const search = document.getElementById('strategy-search');
const rows = Array.from(document.querySelectorAll('.strategy-row'));
const empty = document.getElementById('strategy-empty');
search.addEventListener('input', () => {{
  const query = search.value.toLowerCase();
  let visible = 0;
  for (const row of rows) {{
    const match = row.innerText.toLowerCase().includes(query);
    row.hidden = !match;
    if (match) visible += 1;
  }}
  empty.hidden = visible !== 0;
}});
</script>
"""
    return _page_shell("Strategy Index", body)


def write_curated_strategy_guides(output_dir: Path) -> list[Path]:
    """Copy every packaged curated guide into a strategy output directory."""

    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for guide in CURATED_STRATEGY_GUIDES:
        source = CURATED_STRATEGY_GUIDES_DIRECTORY / guide.filename
        destination = output_dir / guide.filename
        copyfile(source, destination)
        written.append(destination)
    return written


def render_strategy_pages(
    output_dir: Path,
    *,
    names: Iterable[str] | None = None,
    loader: StrategyLoader | None = None,
) -> list[Path]:
    """Write strategy HTML pages and return created paths."""

    output_dir.mkdir(parents=True, exist_ok=True)
    items = collect_rendered_strategies(loader, names=names)
    written = write_curated_strategy_guides(output_dir)

    index_path = output_dir / "index.html"
    index_path.write_text(
        render_strategy_index(items, curated_guides=CURATED_STRATEGY_GUIDES),
        encoding="utf-8",
    )
    written.append(index_path)

    for item in items:
        path = output_dir / f"{item.slug}.html"
        path.write_text(render_strategy_page(item), encoding="utf-8")
        written.append(path)

    return written
