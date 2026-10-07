"""Predicate identity must survive worker transport without conflating policies."""

from copy import deepcopy
from functools import partial
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace

import cloudpickle
import pytest

from dominion.strategy.condition_signature import UnsupportedConditionFingerprint, condition_signature


def _matching_names(names):
    return lambda state, player: player.name in names


def _minimum_coins(state, player, *, minimum):
    return player.coins >= minimum


class _Threshold:
    __slots__ = ("minimum",)

    def __init__(self, minimum):
        self.minimum = minimum

    def __call__(self, state, player):
        return player.coins >= self.minimum


def _worker_signature(blob):
    return condition_signature(cloudpickle.loads(blob))


def test_equal_captured_strings_do_not_depend_on_pickle_memo_sharing():
    name = "Colony engine with a custom condition"
    separate = name.encode().decode()
    assert name == separate and name is not separate
    shared = _matching_names([name, name])
    copied = _matching_names([name, separate])
    assert cloudpickle.dumps(shared) != cloudpickle.dumps(copied)
    # A value-only predicate does not observe incidental scalar aliases.
    assert condition_signature(shared) == condition_signature(copied)
    for predicate in [shared, copied]:
        expected = condition_signature(predicate)
        assert condition_signature(deepcopy(predicate)) == expected
        for _ in range(3):
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected


@pytest.mark.parametrize(
    "predicate",
    [
        _matching_names(["Colony", "Province"]),
        partial(_minimum_coins, minimum=8),
        _Threshold(8),
        _Threshold(8).__call__,
    ],
)
def test_custom_predicate_identity_survives_copy_and_transport(predicate):
    expected = condition_signature(predicate)
    assert condition_signature(deepcopy(predicate)) == expected
    for _ in range(3):
        predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
        assert condition_signature(predicate) == expected


def test_worker_process_computes_same_identity():
    predicate = _matching_names(["Colony", "Province"])
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        result = pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(
            timeout=20
        )
    assert result == condition_signature(predicate)


@pytest.mark.parametrize(
    "factory",
    [
        lambda n: partial(_minimum_coins, minimum=n),
        _Threshold,
        lambda n: lambda state, player, *, minimum=n: player.coins >= minimum,
    ],
)
def test_different_thresholds_remain_distinct(factory):
    assert condition_signature(factory(4)) != condition_signature(factory(8))


def test_nested_helper_code_and_closure_values_remain_distinct():
    def gate(multiplier):
        def helper(amount):
            return amount * multiplier

        return lambda state, player: helper(player.coins) >= 8

    assert condition_signature(gate(1)) != condition_signature(gate(2))
    assert condition_signature(gate(2)) == condition_signature(gate(2))


def test_recursive_closure_survives_transport():
    def predicate(state, player):
        return player.coins > 0 or predicate(state, SimpleNamespace(coins=1))

    assert condition_signature(predicate) == condition_signature(
        cloudpickle.loads(cloudpickle.dumps(predicate))
    )


def test_global_configuration_is_part_of_identity():
    namespace = {"LIMIT": 4}
    exec("def predicate(state, player): return player.coins >= LIMIT", namespace)
    first = condition_signature(namespace["predicate"])
    namespace["LIMIT"] = 8
    assert first != condition_signature(namespace["predicate"])


def test_extension_values_survive_transport():
    pattern = re.compile("Colony|Province")
    predicate = lambda state, player: pattern.fullmatch(player.name) is not None
    assert condition_signature(predicate) == condition_signature(
        cloudpickle.loads(cloudpickle.dumps(predicate))
    )


def test_bound_builtin_in_closure_includes_its_owner():
    def gate(names):
        contains = names.__contains__
        return lambda state, player: contains(player.name)

    assert condition_signature(gate(["Colony"])) != condition_signature(
        gate(["Province"])
    )
    predicate = gate(["Colony"])
    assert condition_signature(predicate) == condition_signature(
        cloudpickle.loads(cloudpickle.dumps(predicate))
    )


def test_global_helper_closures_with_the_same_name_remain_distinct():
    def helper_factory(minimum):
        return lambda player: player.coins >= minimum

    def predicate_factory(minimum):
        namespace = {"__name__": __name__, "helper": helper_factory(minimum)}
        exec("def predicate(state, player): return helper(player)", namespace)
        return namespace["predicate"]

    first = predicate_factory(4)
    second = predicate_factory(8)
    assert condition_signature(first) != condition_signature(second)
    assert condition_signature(first) == condition_signature(
        cloudpickle.loads(cloudpickle.dumps(first))
    )


def test_callable_class_closure_parameters_remain_distinct():
    def factory(minimum):
        class Gate:
            def __call__(self, state, player):
                return player.coins >= minimum

        return Gate()

    first = factory(4)
    assert condition_signature(first) != condition_signature(factory(8))
    assert condition_signature(first) == condition_signature(
        cloudpickle.loads(cloudpickle.dumps(first))
    )


@pytest.mark.parametrize("method_kind", ["static", "class", "property"])
def test_captured_local_class_behavior_remains_distinct_after_transport(method_kind):
    def factory(minimum):
        class Gate:
            @staticmethod
            def static_gate(player):
                return player.coins >= minimum

            @classmethod
            def class_gate(cls, player):
                return player.coins >= minimum

            @property
            def threshold(self):
                return minimum

        if method_kind == "static":
            return lambda state, player: Gate.static_gate(player)
        if method_kind == "class":
            return lambda state, player: Gate.class_gate(player)
        return lambda state, player: player.coins >= Gate().threshold

    first = factory(4)
    assert first(None, SimpleNamespace(coins=6))
    assert not factory(8)(None, SimpleNamespace(coins=6))
    expected = condition_signature(first)
    assert expected != condition_signature(factory(8))
    assert expected == condition_signature(factory(4))
    assert expected == condition_signature(deepcopy(first))
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for _ in range(3):
            first = cloudpickle.loads(cloudpickle.dumps(first))
            assert condition_signature(first) == expected
        assert pool.submit(_worker_signature, cloudpickle.dumps(first)).result(timeout=20) == expected



def test_callable_local_object_includes_helper_method_closure():
    def factory(minimum):
        class Gate:
            def check(self, player):
                return player.coins >= minimum

            def __call__(self, state, player):
                return self.check(player)

        return Gate()

    first = factory(4)
    assert first(None, SimpleNamespace(coins=6))
    assert not factory(8)(None, SimpleNamespace(coins=6))
    expected = condition_signature(first)
    assert expected != condition_signature(factory(8))
    assert expected == condition_signature(factory(4))
    assert expected == condition_signature(deepcopy(first))
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for _ in range(3):
            first = cloudpickle.loads(cloudpickle.dumps(first))
            assert condition_signature(first) == expected
        assert pool.submit(_worker_signature, cloudpickle.dumps(first)).result(timeout=20) == expected


@pytest.mark.parametrize("container", [list, dict, set, lambda: frozenset({1}), lambda: tuple([1])])
def test_captured_container_alias_topology_survives_transport(container):
    def factory(shared):
        a = container()
        b = a if shared else container()
        return lambda state, player: a is b

    shared, separate = factory(True), factory(False)
    assert shared(None, None) and not separate(None, None)
    assert condition_signature(shared) != condition_signature(separate)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for predicate in [shared, separate]:
            expected = condition_signature(predicate)
            assert condition_signature(deepcopy(predicate)) == expected
            for _ in range(3):
                predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
                assert condition_signature(predicate) == expected
            assert pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(timeout=20) == expected


def test_mutable_aliases_across_nested_containers_and_cycles_remain_distinct():
    def factory(shared):
        a = []
        a.append(a)
        b = a if shared else []
        if not shared:
            b.append(b)
        captured = {"a": [a], "b": [b]}
        return lambda state, player: captured["a"][0] is captured["b"][0]

    assert condition_signature(factory(True)) != condition_signature(factory(False))
    for shared in [True, False]:
        predicate = factory(shared)
        assert condition_signature(predicate) == condition_signature(deepcopy(predicate))
        assert condition_signature(predicate) == condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate)))



@pytest.mark.parametrize("callable_kind", ["function", "partial", "method"])
def test_captured_callable_alias_topology_survives_copy_and_worker_transport(callable_kind):
    def helper_factory():
        if callable_kind == "function":
            return lambda player: player.coins >= 4
        if callable_kind == "partial":
            return partial(_minimum_coins, minimum=4)
        return _Threshold(4).__call__

    def factory(shared):
        a = helper_factory()
        b = a if shared else helper_factory()
        return lambda state, player: a is b

    shared, separate = factory(True), factory(False)
    assert shared(None, None) and not separate(None, None)
    assert condition_signature(shared) != condition_signature(separate)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for predicate in [shared, separate]:
            expected = condition_signature(predicate)
            assert condition_signature(deepcopy(predicate)) == expected
            for _ in range(3):
                predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
                assert condition_signature(predicate) == expected
            assert pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(timeout=20) == expected


@pytest.mark.parametrize("container", [set, frozenset])
def test_unordered_identity_hashed_objects_have_stable_reference_markers(container):
    class Limit:
        def __init__(self, limit):
            self.limit = limit

    limits = container(Limit(n) for n in range(12))
    predicate = lambda state, player: any(item.limit == player.coins for item in limits)
    expected = condition_signature(predicate)
    assert predicate(None, SimpleNamespace(coins=4))
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for _ in range(12):
            assert condition_signature(deepcopy(predicate)) == expected
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected
        assert pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(timeout=20) == expected



def test_equal_unordered_members_with_external_alias_have_stable_graph_labels():
    class Limit:
        def __init__(self, limit):
            self.limit = limit

    def factory(extra_alias):
        anchor = Limit(4)
        limits = {anchor, *(Limit(4) for _ in range(5))}
        selected = anchor if extra_alias else Limit(4)
        return lambda state, player: selected in limits

    included, excluded = factory(True), factory(False)
    assert included(None, None) and not excluded(None, None)
    assert condition_signature(included) != condition_signature(excluded)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for predicate in [included, excluded]:
            expected = condition_signature(predicate)
            for _ in range(8):
                predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
                assert condition_signature(predicate) == expected
            assert pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(timeout=20) == expected


def test_unordered_reference_graph_distinguishes_cycles_and_shared_edges():
    class Node:
        pass

    def factory(shared):
        nodes = [Node() for _ in range(4)]
        for i, node in enumerate(nodes):
            node.next = nodes[(i + 1) % len(nodes)]
        if shared:
            nodes[1].next = nodes[0]
        captured = set(nodes)
        return lambda state, player: any(node.next.next is node for node in captured)

    first, second = factory(True), factory(False)
    assert first(None, None) and not second(None, None)
    assert condition_signature(first) != condition_signature(second)
    for predicate in [first, second]:
        expected = condition_signature(predicate)
        for _ in range(5):
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected



def test_canonical_graph_distinguishes_equal_degree_cycle_topologies():
    class Node:
        pass

    def factory(cycle_size):
        nodes = [Node() for _ in range(6)]
        for start in range(0, 6, cycle_size):
            for i in range(cycle_size):
                nodes[start + i].next = nodes[start + (i + 1) % cycle_size]
        captured = frozenset(nodes)
        return lambda state, player: any(node.next.next.next is node for node in captured)

    triangles, hexagon = factory(3), factory(6)
    assert triangles(None, None) and not hexagon(None, None)
    assert condition_signature(triangles) != condition_signature(hexagon)
    for predicate in [triangles, hexagon]:
        expected = condition_signature(predicate)
        for _ in range(4):
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected



@pytest.mark.parametrize("scalar_factory", [
    lambda: "a dynamically created captured string with several words".encode().decode(),
    lambda: bytes(bytearray(b"a dynamically created captured bytes value")),
])
@pytest.mark.parametrize("observer", ["is", "id", "operator"])
def test_memoized_scalar_alias_behavior_and_transport_are_preserved(scalar_factory, observer):
    def factory(shared):
        a = scalar_factory()
        b = a if shared else scalar_factory()
        if observer == "id":
            return lambda state, player: id(a) == id(b)
        if observer == "operator":
            from operator import is_ as compare
            return lambda state, player: compare(a, b)
        return lambda state, player: a is b

    shared, separate = factory(True), factory(False)
    assert shared(None, None) and not separate(None, None)
    assert condition_signature(shared) != condition_signature(separate)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        for predicate in [shared, separate]:
            expected = condition_signature(predicate)
            assert condition_signature(deepcopy(predicate)) == expected
            for _ in range(3):
                predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
                assert condition_signature(predicate) == expected
            assert pool.submit(_worker_signature, cloudpickle.dumps(predicate)).result(timeout=20) == expected


@pytest.mark.parametrize("kind", ["function", "partial"])
def test_callable_attribute_state_controls_identity_and_survives_transport(kind):
    def factory(threshold):
        if kind == "function":
            def helper(player):
                return player.coins >= helper.threshold
            decision = lambda state, player: helper(player)
        else:
            def read_attribute(state, player, *, policy):
                return player.coins >= policy.threshold
            helper = partial(read_attribute, policy=None)
            helper.keywords["policy"] = helper
            decision = lambda state, player: helper(state, player)
        helper.threshold = threshold
        # Self-referencing attribute state exercises graph cycles as well.
        helper.policy = helper
        return decision

    first, second = factory(4), factory(8)
    assert first(None, SimpleNamespace(coins=6))
    assert not second(None, SimpleNamespace(coins=6))
    assert condition_signature(first) != condition_signature(second)
    with ProcessPoolExecutor(
        max_workers=1, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        expected = condition_signature(first)
        for _ in range(3):
            first = cloudpickle.loads(cloudpickle.dumps(first))
            assert condition_signature(first) == expected
        assert pool.submit(_worker_signature, cloudpickle.dumps(first)).result(timeout=20) == expected



def test_cross_module_global_helpers_include_attribute_state():
    def helper_factory(threshold):
        def helper(player):
            return player.coins >= helper.threshold
        helper.threshold = threshold
        return helper

    def factory(threshold):
        namespace = {"__name__": "other_policy_module", "helper": helper_factory(threshold)}
        exec("def predicate(state, player): return helper(player)", namespace)
        return namespace["predicate"]

    first, second = factory(4), factory(8)
    assert first(None, SimpleNamespace(coins=6))
    assert not second(None, SimpleNamespace(coins=6))
    assert condition_signature(first) != condition_signature(second)
    assert condition_signature(first) == condition_signature(cloudpickle.loads(cloudpickle.dumps(first)))



@pytest.mark.parametrize("capture", ["class", "instance", "metaclass"])
def test_custom_metaclass_requires_explicit_source_signature(capture):
    def factory(minimum):
        class Meta(type):
            @property
            def minimum(cls):
                return minimum
        class Gate(metaclass=Meta):
            pass
        if capture == "class":
            return lambda state, player: player.coins >= Gate.minimum
        if capture == "instance":
            gate = Gate()
            return lambda state, player: player.coins >= type(gate).minimum
        return lambda state, player: Meta

    for minimum in [4, 8]:
        predicate = factory(minimum)
        with pytest.raises(UnsupportedConditionFingerprint, match="metaclass.*_source"):
            condition_signature(predicate)
        predicate._source = f"custom metaclass {capture} minimum={minimum}"
        assert condition_signature(predicate) == ("source", predicate._source)
        assert condition_signature(predicate) == condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate)))


@pytest.mark.parametrize("base,initial", [
    (str, "same text"), (bytes, b"same bytes"), (int, 1), (float, 1.0),
    (complex, 1j), (bytearray, b"same bytes"), (tuple, [1]), (list, [1]),
    (dict, {}), (set, [1]), (frozenset, [1]),
])
def test_stateful_builtin_subclasses_require_explicit_source_signature(base, initial):
    class Stateful(base):
        pass
    def factory(minimum):
        captured = Stateful(initial)
        captured.minimum = minimum
        return lambda state, player: player.coins >= captured.minimum

    low, high = factory(4), factory(8)
    assert low(None, SimpleNamespace(coins=6))
    assert not high(None, SimpleNamespace(coins=6))
    for predicate, minimum in [(low, 4), (high, 8)]:
        for _ in range(3):
            with pytest.raises(UnsupportedConditionFingerprint, match="subclass.*_source"):
                condition_signature(predicate)
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
        predicate._source = f"{base.__name__} subclass minimum={minimum}"
        assert condition_signature(predicate) == ("source", predicate._source)


def test_standard_imported_enums_remain_supported():
    from dominion.cards.base_card import CardType
    kind = CardType.ACTION
    predicate = lambda state, player: kind in player.types
    assert condition_signature(predicate) == condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate)))



@pytest.mark.parametrize("kind", ["partial", "staticmethod", "classmethod", "property", "module"])
def test_custom_callable_descriptor_and_module_subclasses_require_source(kind):
    from types import ModuleType
    base = {"partial": partial, "staticmethod": staticmethod, "classmethod": classmethod,
            "property": property, "module": ModuleType}[kind]
    class Stateful(base):
        pass
    if kind == "partial":
        captured = Stateful(_minimum_coins, minimum=4)
    elif kind == "module":
        captured = Stateful("custom_policy")
    else:
        captured = Stateful(lambda *_: True)
    captured.minimum = 4
    predicate = lambda state, player: captured.minimum <= player.coins
    with pytest.raises(UnsupportedConditionFingerprint, match="subclass.*_source"):
        condition_signature(predicate)


def test_standard_counter_preserves_mapping_and_rejects_unserializable_attributes():
    from collections import Counter
    captured = Counter({"Copper": 3})
    predicate = lambda state, player: captured["Copper"] + player.coins >= 4
    assert condition_signature(predicate) == condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate)))
    captured.minimum = 4
    with pytest.raises(UnsupportedConditionFingerprint, match="Counter attribute state.*_source"):
        condition_signature(predicate)


@pytest.mark.parametrize("name", ["ref", "reference", "mutable", "set", "frozenset"])
@pytest.mark.parametrize("location", ["argument", "global", "class"])
def test_graph_markers_cannot_collide_with_user_names(name, location):
    if location == "argument":
        namespace = {}
        exec(f"def predicate({name}, player): return player.coins >= 4", namespace)
        predicate = namespace["predicate"]
    elif location == "global":
        namespace = {name: [4]}
        exec(f"def predicate(state, player): return player.coins >= {name}[0]", namespace)
        predicate = namespace["predicate"]
    else:
        class Gate:
            pass
        setattr(Gate, name, [4])
        namespace = {"Gate": Gate}
        exec(f"def predicate(state, player): return player.coins >= Gate.{name}[0]", namespace)
        predicate = namespace["predicate"]
    expected = condition_signature(predicate)
    assert predicate(None, SimpleNamespace(coins=6))
    for _ in range(3):
        predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
        assert condition_signature(predicate) == expected


def test_three_argument_mutable_name_is_not_a_node_marker():
    predicate = lambda mutable, marker, value: bool(value)
    expected = condition_signature(predicate)
    assert condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate))) == expected


@pytest.mark.parametrize("registered", [False, True])
def test_dynamic_modules_require_explicit_source(registered):
    import sys
    from types import ModuleType

    for threshold in [4, 8]:
        policy = ModuleType("fingerprint_dynamic_policy")
        policy.minimum = threshold
        if registered:
            sys.modules[policy.__name__] = policy
        try:
            predicate = lambda state, player: player.coins >= policy.minimum
            with pytest.raises(UnsupportedConditionFingerprint, match="Dynamic modules"):
                condition_signature(predicate)
            predicate._source = f"dynamic policy minimum={threshold}"
            assert condition_signature(predicate) == ("source", predicate._source)
        finally:
            if registered:
                del sys.modules[policy.__name__]


@pytest.mark.parametrize("attribute", ["__annotations__", "__name__", "__qualname__", "__module__", "__doc__"])
def test_special_function_metadata_distinguishes_policies(attribute):
    def factory(threshold):
        def helper(state, player):
            value = getattr(helper, attribute)
            minimum = value["minimum"] if attribute == "__annotations__" else int(value)
            return player.coins >= minimum
        setattr(helper, attribute, {"minimum": threshold} if attribute == "__annotations__" else str(threshold))
        return lambda state, player: helper(state, player)

    first, second = factory(4), factory(8)
    assert first(None, SimpleNamespace(coins=6))
    assert not second(None, SimpleNamespace(coins=6))
    assert condition_signature(first) != condition_signature(second)
    for predicate in [first, second]:
        expected = condition_signature(predicate)
        assert condition_signature(deepcopy(predicate)) == expected
        for _ in range(3):
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected


@pytest.mark.parametrize("kind", ["datetime", "date", "time", "timedelta", "decimal", "fraction", "range", "slice"])
def test_supported_opaque_values_preserve_alias_topology(kind):
    import datetime
    from decimal import Decimal
    from fractions import Fraction

    factories = {
        "datetime": lambda: datetime.datetime(2026, 10, 7),
        "date": lambda: datetime.date(2026, 10, 7),
        "time": lambda: datetime.time(12, 34),
        "timedelta": lambda: datetime.timedelta(days=4),
        "decimal": lambda: Decimal("4.25"),
        "fraction": lambda: Fraction(17, 4),
        "range": lambda: range(4),
        "slice": lambda: slice(4),
    }
    def predicate(shared):
        a = factories[kind]()
        b = a if shared else factories[kind]()
        return lambda state, player: a is b

    first, second = predicate(True), predicate(False)
    assert first(None, None) and not second(None, None)
    assert condition_signature(first) != condition_signature(second)
    for value in [first, second]:
        expected = condition_signature(value)
        for _ in range(3):
            value = cloudpickle.loads(cloudpickle.dumps(value))
            assert condition_signature(value) == expected


@pytest.mark.parametrize("kind", ["object", "memoryview", "iterator", "generator", "mappingproxy", "datetime_subclass", "reducer"])
def test_unsupported_leaf_families_require_explicit_source(kind):
    import datetime
    from types import MappingProxyType

    class CustomDate(datetime.date):
        pass

    class Reduced:
        def __init__(self):
            self.minimum = 4

        def __getstate__(self):
            return {}

    values = {
        "object": lambda: object(),
        "memoryview": lambda: memoryview(b"policy"),
        "iterator": lambda: iter([4]),
        "generator": lambda: (i for i in [4]),
        "mappingproxy": lambda: MappingProxyType({"minimum": 4}),
        "datetime_subclass": lambda: CustomDate(2026, 10, 7),
        "reducer": Reduced,
    }
    value = values[kind]()
    predicate = lambda state, player: bool(value)
    with pytest.raises(UnsupportedConditionFingerprint):
        condition_signature(predicate)
    predicate._source = f"declared policy {kind} parameter=4"
    assert condition_signature(predicate) == ("source", predicate._source)



def test_supported_extension_nested_state_preserves_cross_value_aliases():
    def factory(shared):
        minimum = [4]
        selection = slice(minimum if shared else [4], None)
        return lambda state, player: selection.start is minimum

    first, second = factory(True), factory(False)
    assert first(None, None) and not second(None, None)
    assert condition_signature(first) != condition_signature(second)
    for predicate in [first, second]:
        expected = condition_signature(predicate)
        for _ in range(3):
            predicate = cloudpickle.loads(cloudpickle.dumps(predicate))
            assert condition_signature(predicate) == expected


def test_custom_timezone_requires_source():
    import datetime

    class Offset(datetime.tzinfo):
        def utcoffset(self, value):
            return datetime.timedelta(hours=4)

    value = datetime.datetime(2026, 10, 7, tzinfo=Offset())
    predicate = lambda state, player: value.hour == player.coins
    with pytest.raises(UnsupportedConditionFingerprint, match="timezone"):
        condition_signature(predicate)



def test_imported_module_remains_supported():
    import math
    predicate = lambda state, player: math.floor(player.coins) >= 4
    expected = condition_signature(predicate)
    assert condition_signature(cloudpickle.loads(cloudpickle.dumps(predicate))) == expected


def test_function_metadata_aliases_remain_distinct():
    def factory(shared):
        def helper():
            pass
        helper.__name__ = "a custom long function name".encode().decode()
        name = helper.__name__ if shared else helper.__name__.encode().decode()
        return lambda state, player: helper.__name__ is name
    first, second = factory(True), factory(False)
    assert first(None, None) and not second(None, None)
    for predicate in [first, second]:
        with pytest.raises(UnsupportedConditionFingerprint, match="metadata identity"):
            condition_signature(predicate)


@pytest.mark.parametrize("kind", [staticmethod, classmethod])
def test_descriptor_custom_attributes_are_not_discarded(kind):
    def factory(threshold):
        descriptor = kind(lambda: None)
        descriptor.minimum = threshold
        return lambda state, player: player.coins >= descriptor.minimum
    first, second = factory(4), factory(8)
    assert first(None, SimpleNamespace(coins=6)) and not second(None, SimpleNamespace(coins=6))
    for predicate in [first, second]:
        with pytest.raises(UnsupportedConditionFingerprint, match="descriptor attributes"):
            condition_signature(predicate)
