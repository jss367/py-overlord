"""Structural fingerprints for custom rule predicates.

Canonicalize code, captured state and the supported reference graph. Containers
and callables preserve aliases. Strings/bytes also preserve aliases when
reachable code explicitly observes identity; value-only code ignores scalar
memoization. Numeric identity and dynamic reflection require an explicit source
signature. Imported code uses shared runtime symbols; callable state is retained.
These fingerprints are not a cross-version checkpoint format.
"""

from collections import Counter
import datetime
from decimal import Decimal
from fractions import Fraction
import dis
from enum import Enum, EnumType
from functools import partial
import hashlib
import json
import re
import sys
import types


_EXTENSION_TYPES = {
    datetime.date, datetime.datetime, datetime.time, datetime.timedelta,
    datetime.timezone, Decimal, Fraction, range, slice, re.Pattern,
}


class UnsupportedConditionFingerprint(ValueError):
    """A captured custom type needs a declared source signature."""


def _check_supported_type(value):
    """Reject custom dispatch/state that the structural encoder cannot model."""
    cls = type(value)
    metaclass = cls if isinstance(value, type) else type(cls)
    standard_enum = (
        metaclass is EnumType
        and _importable_symbol(value if isinstance(value, type) else cls)
    )
    if (
        metaclass is not type and not standard_enum
        and cls not in _EXTENSION_TYPES
        and not (isinstance(value, type) and value in _EXTENSION_TYPES)
    ) or (
        isinstance(value, type) and issubclass(value, type)
        and value not in {type, EnumType}
    ):
        raise UnsupportedConditionFingerprint(
            "Custom metaclasses require an explicit predicate _source signature "
            "covering behavior-controlling state"
        )
    if cls is types.ModuleType and (
        sys.modules.get(value.__name__) is not value or value.__spec__ is None
    ):
        raise UnsupportedConditionFingerprint(
            "Dynamic modules require an explicit predicate _source signature"
        )
    if cls in {datetime.datetime, datetime.time} and (
        value.tzinfo is not None and type(value.tzinfo) is not datetime.timezone
    ):
        raise UnsupportedConditionFingerprint(
            "Custom timezone state requires an explicit predicate _source signature"
        )
    if cls is types.FunctionType and getattr(value, "__type_params__", ()):
        raise UnsupportedConditionFingerprint(
            "Generic function type parameters require an explicit predicate _source signature"
        )
    if cls in {staticmethod, classmethod}:
        if any(
            name not in {"__module__", "__name__", "__qualname__", "__doc__", "__annotations__", "__type_params__"}
            or item != getattr(value.__func__, name, None)
            for name, item in value.__dict__.items()
        ):
            raise UnsupportedConditionFingerprint(
                "Custom descriptor attributes are not transported; use an explicit predicate _source signature"
            )
    if cls is property and value.__doc__ != getattr(value.fget, "__doc__", None):
        raise UnsupportedConditionFingerprint(
            "Custom property documentation requires an explicit predicate _source signature"
        )
    if isinstance(value, Enum) and standard_enum:
        return
    if cls is Counter and value.__dict__:
        raise UnsupportedConditionFingerprint(
            "Counter attribute state is not preserved by pickle; use a serializable "
            "policy representation with an explicit predicate _source signature"
        )
    builtins = (
        int, float, complex, str, bytes, bytearray, tuple, list, dict, set,
        frozenset, partial, staticmethod, classmethod, property, types.ModuleType,
        *tuple(_EXTENSION_TYPES),
    )
    if isinstance(value, builtins) and cls not in builtins and cls not in {bool, Counter}:
        raise UnsupportedConditionFingerprint(
            f"Captured subclass {cls.__module__}.{cls.__qualname__} requires an "
            "explicit predicate _source signature covering behavior-controlling state"
        )

def condition_signature(condition) -> tuple | None:
    """Identify a predicate without depending on pickle's object memo."""
    if condition is None:
        return None
    source = getattr(condition, "_source", None)
    if source is not None:
        return ("source", source)
    identity_observers = []
    frozen = _freeze(condition, {}, identity_observers=identity_observers)
    if identity_observers:
        frozen = _freeze(condition, {}, scalar_aliases=True)
    frozen = _canonical_graph(frozen)
    encoded = json.dumps(frozen, ensure_ascii=True, separators=(",", ":"))
    return ("callable", hashlib.sha256(encoded.encode()).digest())


def _symbol(value):
    return (value.__module__, value.__qualname__)


def _importable_symbol(value):
    """Only shared runtime symbols can safely use module/name identity."""
    current = sys.modules.get(value.__module__)
    for name in value.__qualname__.split("."):
        if current is None or name == "<locals>":
            return False
        current = vars(current).get(name)
    return current is value


def _global_names(code):
    names = {
        instruction.argval
        for instruction in dis.get_instructions(code)
        if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
    }
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            names.update(_global_names(constant))
    return names


def _freeze(value, active, references=None, scalar_aliases=False, identity_observers=None):
    """Capture containers and callables as nodes; ignore scalar memoization."""
    _check_supported_type(value)
    if references is None:
        references = {}
    mutable = isinstance(value, (
        list, tuple, dict, set, frozenset, bytearray, types.FunctionType, types.MethodType,
        types.BuiltinFunctionType, types.MethodWrapperType, partial,
        staticmethod, classmethod, property, *tuple(_EXTENSION_TYPES),
    )) or (scalar_aliases and isinstance(value, (str, bytes))) or (isinstance(value, type) and not _importable_symbol(value)) or (
        not isinstance(value, (
            type, types.ModuleType, types.FunctionType, types.MethodType,
            types.BuiltinFunctionType, types.CodeType, staticmethod, classmethod,
            property, partial,
        ))
        and (hasattr(value, "__dict__") or any(
            "__slots__" in cls.__dict__ for cls in type(value).__mro__
        ))
    )
    if mutable:
        identity = id(value)
        if identity in references:
            return {"reference": references[identity][0]}
        marker = len(references)
        # Retain objects too: synthesized slot-state dictionaries can otherwise
        # be freed and their IDs reused during a later sibling's traversal.
        references[identity] = (marker, value)
        return {"mutable": marker, "value": _freeze_value(value, active, references, scalar_aliases, identity_observers)}
    return _freeze_value(value, active, references, scalar_aliases, identity_observers)


def _function_metadata(value, freeze):
    """Preserved function attributes that live outside its attribute dictionary."""
    _check_supported_type(value)
    return (
        "metadata", value.__name__, value.__qualname__, value.__module__,
        value.__doc__, freeze(value.__annotations__),
    )


def _freeze_value(value, active, references, scalar_aliases, identity_observers):
    """Build JSON values with active recursion and graph-reference tracking."""
    if isinstance(value, Enum):
        return ("runtime-enum", _symbol(type(value)), value.name)
    if value is None or type(value) in {bool, int, str}:
        return (type(value).__name__, value)
    if type(value) is float:
        return ("float", value.hex())
    if type(value) is complex:
        return ("complex", value.real.hex(), value.imag.hex())
    if type(value) is bytes:
        return ("bytes", value.hex())
    if value is Ellipsis:
        return ("ellipsis",)
    if isinstance(value, types.ModuleType):
        return ("module", value.__name__)
    if isinstance(value, type) and _importable_symbol(value):
        return ("symbol", _symbol(value))

    identity = id(value)
    if identity in active:
        return ("cycle", active[identity])
    active[identity] = len(active)
    try:
        freeze = lambda item: _freeze(item, active, references, scalar_aliases, identity_observers)
        if isinstance(value, type):
            # Local/by-value classes can share names but capture different
            # method parameters. Descriptor wrappers must expose their code.
            attributes = []
            for name, item in sorted(vars(value).items()):
                if name in {"__dict__", "__weakref__", "__module__", "__qualname__", "__firstlineno__", "__slotnames__", "__static_attributes__"}:
                    continue
                if isinstance(item, (types.MemberDescriptorType, types.GetSetDescriptorType)):
                    continue
                attributes.append((name, freeze(item)))
            return ("class", value.__name__, ("bases", [freeze(base) for base in value.__bases__]), attributes)
        if isinstance(value, (staticmethod, classmethod)):
            return (type(value).__name__, freeze(value.__func__))
        if isinstance(value, property):
            return ("property", freeze(value.fget), freeze(value.fset), freeze(value.fdel), freeze(value.__doc__))
        if isinstance(value, (types.BuiltinFunctionType, types.MethodWrapperType)):
            if (
                identity_observers is not None
                and getattr(value, "__module__", None) in {"builtins", "operator", "_operator"}
                and value.__name__ in {"id", "is_", "is_not"}
            ):
                identity_observers.append(True)
            owner = getattr(value, "__self__", None)
            if owner is not None and not isinstance(owner, types.ModuleType):
                return ("bound-builtin", value.__name__, freeze(owner))
            return ("symbol", _symbol(value))
        if isinstance(value, types.CodeType):
            instructions = list(dis.get_instructions(value))
            if any(i.opname == "LOAD_ATTR" and i.argval in {
                "__name__", "__qualname__", "__module__", "__doc__"
            } for i in instructions) and any(
                i.opname == "IS_OP" or i.argval in {"id", "is_", "is_not"}
                for i in instructions if isinstance(i.argval, (str, int, type(None)))
            ):
                raise UnsupportedConditionFingerprint(
                    "Function metadata identity is not transport stable; use an explicit predicate _source signature"
                )
            if identity_observers is not None:
                previous = None
                for instruction in dis.get_instructions(value):
                    if (
                        instruction.opname == "IS_OP"
                        and not (
                            previous is not None and (
                                (previous.opname == "LOAD_CONST" and previous.argval is None)
                                # Python 3.14's optimized any/all guards compare
                                # builtins with compiler-owned common constants.
                                or previous.opname == "LOAD_COMMON_CONSTANT"
                            )
                        )
                    ) or (
                        instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME", "LOAD_ATTR"}
                        and instruction.argval in {"id", "is_", "is_not"}
                    ):
                        identity_observers.append(True)
                    previous = instruction
            return (
                "code",
                value.co_code.hex(),
                value.co_exceptiontable.hex(),
                value.co_argcount,
                value.co_posonlyargcount,
                value.co_kwonlyargcount,
                value.co_flags,
                value.co_names,
                value.co_varnames,
                value.co_freevars,
                value.co_cellvars,
                ("constants", [freeze(item) for item in value.co_consts]),
            )
        if isinstance(value, types.FunctionType):
            closure = []
            for cell in value.__closure__ or ():
                try:
                    captured = cell.cell_contents
                except ValueError:
                    closure.append(("empty-cell",))
                else:
                    closure.append(freeze(captured))
            globals_used = []
            for name in sorted(_global_names(value.__code__)):
                if name not in value.__globals__:
                    continue
                dependency = value.__globals__[name]
                # Imported helpers belong to the shared runtime. Helpers
                # defined alongside the predicate can have distinct code or
                # captured parameters, even when their names are identical.
                frozen = (
                    ("runtime-function", _symbol(dependency),
                     freeze(dependency.__defaults__), freeze(dependency.__kwdefaults__),
                     freeze(dependency.__dict__), _function_metadata(dependency, freeze))
                    if isinstance(dependency, types.FunctionType)
                    and dependency.__module__ != value.__module__
                    and _importable_symbol(dependency)
                    else freeze(dependency)
                )
                globals_used.append((name, frozen))
            return (
                "function",
                freeze(value.__code__),
                freeze(value.__defaults__),
                freeze(value.__kwdefaults__),
                closure,
                globals_used,
                freeze(value.__dict__),
                _function_metadata(value, freeze),
            )
        if isinstance(value, types.MethodType):
            return ("method", freeze(value.__func__), freeze(value.__self__))
        if isinstance(value, partial):
            return (
                "partial",
                freeze(value.func),
                freeze(value.args),
                freeze(value.keywords),
                freeze(value.__dict__),
            )
        if isinstance(value, (tuple, list)):
            return (type(value).__name__, [freeze(item) for item in value])
        if type(value) is Counter:
            return (
                "counter",
                [(freeze(key), freeze(item)) for key, item in value.items()],
            )
        if isinstance(value, dict):
            return (
                "dict",
                [(freeze(key), freeze(item)) for key, item in value.items()],
            )
        if isinstance(value, (set, frozenset)):
            return {"unordered": type(value).__name__, "members": [freeze(item) for item in value]}
        if type(value) is bytearray:
            return ("bytearray", value.hex())
        if type(value) in _EXTENSION_TYPES:
            # Encode nested policy values through the same graph, never through
            # independent pickle blobs that would hide aliases (e.g. slice.start).
            if type(value) is slice:
                state = [value.start, value.stop, value.step]
            elif type(value) is range:
                state = [value.start, value.stop, value.step]
            elif type(value) is re.Pattern:
                state = [value.pattern, value.flags]
            elif type(value) is Decimal:
                state = list(value.as_tuple())
            elif type(value) is Fraction:
                state = [value.numerator, value.denominator]
            elif type(value) is datetime.timedelta:
                state = [value.days, value.seconds, value.microseconds]
            elif type(value) is datetime.timezone:
                state = [value.utcoffset(None), value.tzname(None)]
            else:
                state = []
                if isinstance(value, datetime.date):
                    state.extend([value.year, value.month, value.day])
                if isinstance(value, (datetime.datetime, datetime.time)):
                    state.extend([value.hour, value.minute, value.second,
                                  value.microsecond, value.fold, value.tzinfo])
            return ("extension", _symbol(type(value)), [freeze(item) for item in state])
        if hasattr(value, "__dict__") or any(
            "__slots__" in cls.__dict__ for cls in type(value).__mro__
        ):
            if any(
                getattr(type(value), name, None) is not getattr(object, name)
                for name in ("__getstate__", "__reduce__", "__reduce_ex__")
            ) and type(value) is not types.SimpleNamespace:
                raise UnsupportedConditionFingerprint(
                    "Custom object state reducers require an explicit predicate _source signature"
                )
            call = getattr(type(value), "__call__", None)
            return (
                "object",
                freeze(type(value)),
                freeze(value.__getstate__()),
                freeze(call) if isinstance(call, types.FunctionType) else None,
            )
        raise UnsupportedConditionFingerprint(
            f"Unsupported captured type {type(value).__module__}.{type(value).__qualname__} "
            "requires an explicit predicate _source signature"
        )
    finally:
        del active[identity]


def _canonical_graph(frozen):
    """Label the entire rooted reference graph, including unordered-member ties.

    Reference IDs from traversal are temporary. Ordered edges, unordered set
    edges and incoming aliases refine structural partitions. Remaining ties
    are individualized, choosing the least complete encoding; branches are
    pruned only when an exact color-preserving automorphism is proved.
    """
    nodes = {}

    def extract(value):
        if isinstance(value, dict):
            if "mutable" in value:
                marker = value["mutable"]
                nodes[marker] = extract(value["value"])
                return {"ref": marker}
            if "reference" in value:
                return {"ref": value["reference"]}
            return {"unordered": value["unordered"], "members": extract(value["members"])}
        if isinstance(value, (list, tuple)):
            return tuple(extract(item) for item in value)
        return value

    root = extract(frozen)
    nodes[len(nodes)] = ("root", root)
    graph = [nodes[i] for i in range(len(nodes))]

    def dump(value):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))

    def unordered(value):
        return isinstance(value, dict) and "unordered" in value

    def render(value, labels):
        if unordered(value):
            return {"unordered": value["unordered"], "members": sorted(
                (render(item, labels) for item in value["members"]), key=dump
            )}
        if isinstance(value, dict):
            return {"ref": labels[value["ref"]]}
        if not isinstance(value, tuple):
            return value
        return tuple(render(item, labels) for item in value)

    incoming = [[] for _ in graph]

    def edges(value, source, path=()):
        if unordered(value):
            for item in value["members"]:
                edges(item, source, path + ("member",))
        elif isinstance(value, dict):
            incoming[value["ref"]].append((source, path))
        elif isinstance(value, tuple):
            for position, item in enumerate(value):
                edges(item, source, path + (position,))

    for source, value in enumerate(graph):
        edges(value, source)

    def ranks(keys):
        ordered = {key: rank for rank, key in enumerate(sorted(set(keys)))}
        return [ordered[key] for key in keys]

    def refine(colors):
        while True:
            keys = [
                dump((colors[i], render(value, colors), sorted(
                    ((path, colors[source]) for source, path in incoming[i]), key=dump
                )))
                for i, value in enumerate(graph)
            ]
            updated = ranks(keys)
            # Including the previous color makes refinement split-only.
            if len(set(updated)) == len(set(colors)):
                return updated
            colors = updated

    def equivalent(left, right):
        """Prove a graph automorphism before skipping a symmetric branch."""
        groups = {}
        for node, color in enumerate(right):
            groups.setdefault(color, []).append(node)
        if sorted(left) != sorted(right):
            return False
        mapping = {}
        used = set()

        def consistent():
            a = [("mapped", mapping[i]) if i in mapping else ("color", left[i]) for i in range(len(graph))]
            b = [("mapped", i) if i in used else ("color", right[i]) for i in range(len(graph))]
            return all(render(graph[i], a) == render(graph[j], b) for i, j in mapping.items())

        def match():
            if len(mapping) == len(graph):
                return True
            node = min(
                (i for i in range(len(graph)) if i not in mapping),
                key=lambda i: len([j for j in groups[left[i]] if j not in used]),
            )
            for other in groups[left[node]]:
                if other in used:
                    continue
                mapping[node] = other
                used.add(other)
                if consistent() and match():
                    return True
                used.remove(other)
                del mapping[node]
            return False

        for color, members in groups.items():
            if len(members) == 1:
                node = left.index(color)
                mapping[node] = members[0]
                used.add(members[0])
        return consistent() and match()

    def canonical(colors):
        colors = refine(colors)
        groups = {}
        for node, color in enumerate(colors):
            groups.setdefault(color, []).append(node)
        tied = [members for members in groups.values() if len(members) > 1]
        if not tied:
            order = sorted(range(len(graph)), key=lambda i: colors[i])
            labels = {node: label for label, node in enumerate(order)}
            return dump([render(graph[node], labels) for node in order])
        group = min(tied, key=lambda members: (len(members), colors[members[0]]))
        representatives = []
        best = None
        for node in group:
            branch = refine(ranks([dump((color, i == node)) for i, color in enumerate(colors)]))
            if any(equivalent(branch, previous) for previous in representatives):
                continue
            representatives.append(branch)
            candidate = canonical(branch)
            if best is None or candidate < best:
                best = candidate
        return best

    return json.loads(canonical([0] * len(graph)))
