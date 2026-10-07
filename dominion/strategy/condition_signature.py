"""Structural fingerprints for custom rule predicates.

Pickle is a transport format: its memo records object sharing, so equal scalar
closure values can produce different bytes after copying or a worker round
trip. Freeze function code and captured values before hashing instead, retaining
reference topology for captured containers and callables. Imported symbols are
identified by module and qualified name within the current evaluation runtime;
these fingerprints are not a cross-version checkpoint format.
"""

import dis
from functools import partial
import hashlib
import json
import sys
import types

import cloudpickle


def condition_signature(condition) -> tuple | None:
    """Identify a predicate without depending on pickle's object memo."""
    if condition is None:
        return None
    source = getattr(condition, "_source", None)
    if source is not None:
        return ("source", source)
    frozen = _canonical_graph(_freeze(condition, {}))
    encoded = json.dumps(frozen, ensure_ascii=True, separators=(",", ":"))
    return ("callable", hashlib.sha256(encoded.encode()).digest())


def _symbol(value):
    return (value.__module__, value.__qualname__)


def _importable_type(value):
    """Only shared runtime classes can safely use symbol identity."""
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


def _freeze(value, active, references=None):
    """Capture containers and callables as nodes; ignore scalar memoization."""
    if references is None:
        references = {}
    mutable = isinstance(value, (
        list, tuple, dict, set, frozenset, bytearray, types.FunctionType, types.MethodType,
        types.BuiltinFunctionType, partial,
    )) or (isinstance(value, type) and not _importable_type(value)) or (
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
            return ("reference", references[identity][0])
        marker = len(references)
        # Retain objects too: synthesized slot-state dictionaries can otherwise
        # be freed and their IDs reused during a later sibling's traversal.
        references[identity] = (marker, value)
        return ("mutable", marker, _freeze_value(value, active, references))
    return _freeze_value(value, active, references)


def _freeze_value(value, active, references):
    """Build JSON values with active recursion and graph-reference tracking."""
    if value is None or isinstance(value, (bool, int, str)):
        return (type(value).__name__, value)
    if isinstance(value, float):
        return ("float", value.hex())
    if isinstance(value, complex):
        return ("complex", value.real.hex(), value.imag.hex())
    if isinstance(value, bytes):
        return ("bytes", value.hex())
    if value is Ellipsis:
        return ("ellipsis",)
    if isinstance(value, types.ModuleType):
        return ("module", value.__name__)
    if isinstance(value, type) and _importable_type(value):
        return ("symbol", _symbol(value))

    identity = id(value)
    if identity in active:
        return ("cycle", active[identity])
    active[identity] = len(active)
    try:
        freeze = lambda item: _freeze(item, active, references)
        if isinstance(value, type):
            # Local/by-value classes can share names but capture different
            # method parameters. Descriptor wrappers must expose their code.
            attributes = []
            for name, item in sorted(vars(value).items()):
                if name in {"__dict__", "__weakref__", "__module__", "__qualname__", "__firstlineno__", "__slotnames__"}:
                    continue
                if isinstance(item, (types.MemberDescriptorType, types.GetSetDescriptorType)):
                    continue
                attributes.append((name, freeze(item)))
            return ("class", value.__name__, ("bases", [freeze(base) for base in value.__bases__]), attributes)
        if isinstance(value, (staticmethod, classmethod)):
            return (type(value).__name__, freeze(value.__func__))
        if isinstance(value, property):
            return ("property", freeze(value.fget), freeze(value.fset), freeze(value.fdel))
        if isinstance(value, types.BuiltinFunctionType):
            owner = getattr(value, "__self__", None)
            if owner is not None and not isinstance(owner, types.ModuleType):
                return ("bound-builtin", value.__name__, freeze(owner))
            return ("symbol", _symbol(value))
        if isinstance(value, types.CodeType):
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
                    ("symbol", _symbol(dependency))
                    if isinstance(dependency, types.FunctionType)
                    and dependency.__module__ != value.__module__
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
            )
        if isinstance(value, types.MethodType):
            return ("method", freeze(value.__func__), freeze(value.__self__))
        if isinstance(value, partial):
            return (
                "partial",
                freeze(value.func),
                freeze(value.args),
                freeze(value.keywords),
            )
        if isinstance(value, (tuple, list)):
            return (type(value).__name__, [freeze(item) for item in value])
        if isinstance(value, dict):
            return (
                "dict",
                [(freeze(key), freeze(item)) for key, item in value.items()],
            )
        if isinstance(value, (set, frozenset)):
            return (type(value).__name__, [freeze(item) for item in value])
        if hasattr(value, "__dict__") or any(
            "__slots__" in cls.__dict__ for cls in type(value).__mro__
        ):
            call = getattr(type(value), "__call__", None)
            return (
                "object",
                freeze(type(value)),
                freeze(value.__getstate__()),
                freeze(call) if isinstance(call, types.FunctionType) else None,
            )
        # Extension values such as compiled regexes and NumPy scalars have
        # their own pickle reducers. Serialize each opaque leaf separately,
        # so its memo cannot depend on sharing elsewhere in the predicate.
        return ("opaque", cloudpickle.dumps(value).hex())
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
        if isinstance(value, (list, tuple)):
            if len(value) == 3 and value[0] == "mutable":
                marker = value[1]
                nodes[marker] = extract(value[2])
                return ("ref", marker)
            if len(value) == 2 and value[0] == "reference":
                return ("ref", value[1])
            return tuple(extract(item) for item in value)
        return value

    root = extract(frozen)
    nodes[len(nodes)] = ("root", root)
    graph = [nodes[i] for i in range(len(nodes))]

    def dump(value):
        return json.dumps(value, ensure_ascii=True, separators=(",", ":"))

    def unordered(value):
        return (
            len(value) == 2 and value[0] in {"set", "frozenset"}
            and isinstance(value[1], tuple)
        )

    def render(value, labels):
        if not isinstance(value, tuple):
            return value
        if len(value) == 2 and value[0] == "ref":
            return ("ref", labels[value[1]])
        if unordered(value):
            return (value[0], sorted((render(item, labels) for item in value[1]), key=dump))
        return tuple(render(item, labels) for item in value)

    incoming = [[] for _ in graph]

    def edges(value, source, path=()):
        if not isinstance(value, tuple):
            return
        if len(value) == 2 and value[0] == "ref":
            incoming[value[1]].append((source, path))
        elif unordered(value):
            for item in value[1]:
                edges(item, source, path + ("member",))
        else:
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
