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


@pytest.mark.parametrize("container", [list, dict, set])
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
