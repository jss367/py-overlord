"""Predicate identity must survive worker transport without conflating policies."""

from copy import deepcopy
from functools import partial
import multiprocessing
import re
from concurrent.futures import ProcessPoolExecutor
from types import SimpleNamespace

import cloudpickle
import pytest

from dominion.strategy.condition_signature import condition_signature


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
    assert condition_signature(shared) == condition_signature(copied)


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
def test_mutable_closure_alias_topology_affects_identity_and_survives_transport(container):
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
