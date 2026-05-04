"""Registry of all 15 Plunder Traits.

Each trait registers state on the ``GameState`` via ``apply``. The engine
consults that state at the appropriate hook (see ``GameState.gain_card``,
``handle_cleanup_phase``, ``handle_start_phase``, ``trash_card``,
``shuffle_discard_into_deck``, etc.) without needing to know which traits
exist.
"""

from .base_trait import Trait


def _ensure_state(game_state) -> None:
    """Initialize the trait state containers on ``game_state`` lazily."""
    if not hasattr(game_state, "trait_piles") or game_state.trait_piles is None:
        game_state.trait_piles = {}
    if not hasattr(game_state, "pile_traits") or game_state.pile_traits is None:
        game_state.pile_traits = {}
    if not hasattr(game_state, "hasty_set_aside") or game_state.hasty_set_aside is None:
        game_state.hasty_set_aside = {}
    if not hasattr(game_state, "patient_mat") or game_state.patient_mat is None:
        game_state.patient_mat = {}


def _register(game_state, trait_name: str, pile_name: str) -> None:
    _ensure_state(game_state)
    game_state.trait_piles[trait_name] = pile_name
    game_state.pile_traits[pile_name] = trait_name


class CheapTrait(Trait):
    def __init__(self):
        super().__init__("Cheap")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Cheap", target_pile_name)


class CursedTrait(Trait):
    def __init__(self):
        super().__init__("Cursed")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Cursed", target_pile_name)


class FatedTrait(Trait):
    def __init__(self):
        super().__init__("Fated")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Fated", target_pile_name)
        for player in game_state.players:
            player.fated_pile = target_pile_name


class FriendlyTrait(Trait):
    def __init__(self):
        super().__init__("Friendly")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Friendly", target_pile_name)


class HastyTrait(Trait):
    def __init__(self):
        super().__init__("Hasty")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Hasty", target_pile_name)


class InheritedTrait(Trait):
    def __init__(self):
        super().__init__("Inherited")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Inherited", target_pile_name)
        from dominion.cards.registry import get_card

        for player in game_state.players:
            estates = [c for c in player.deck if c.name == "Estate"]
            if not estates:
                continue
            estate = estates[0]
            player.deck.remove(estate)
            try:
                replacement = get_card(target_pile_name)
            except ValueError:
                player.deck.append(estate)
                continue
            if game_state.supply.get(target_pile_name, 0) <= 0:
                player.deck.append(estate)
                continue
            game_state.supply[target_pile_name] -= 1
            player.deck.append(replacement)


class InspiringTrait(Trait):
    def __init__(self):
        super().__init__("Inspiring")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Inspiring", target_pile_name)


class NearbyTrait(Trait):
    def __init__(self):
        super().__init__("Nearby")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Nearby", target_pile_name)


class PatientTrait(Trait):
    def __init__(self):
        super().__init__("Patient")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Patient", target_pile_name)


class PiousTrait(Trait):
    def __init__(self):
        super().__init__("Pious")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Pious", target_pile_name)


class RecklessTrait(Trait):
    def __init__(self):
        super().__init__("Reckless")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Reckless", target_pile_name)


class RichTrait(Trait):
    def __init__(self):
        super().__init__("Rich")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Rich", target_pile_name)


class ShyTrait(Trait):
    def __init__(self):
        super().__init__("Shy")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Shy", target_pile_name)


class TirelessTrait(Trait):
    def __init__(self):
        super().__init__("Tireless")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Tireless", target_pile_name)
        game_state.tireless_piles.add(target_pile_name)


class FawningTrait(Trait):
    def __init__(self):
        super().__init__("Fawning")

    def apply(self, game_state, target_pile_name: str) -> None:
        _register(game_state, "Fawning", target_pile_name)


TRAITS: dict[str, type] = {
    "Cheap": CheapTrait,
    "Cursed": CursedTrait,
    "Fated": FatedTrait,
    "Friendly": FriendlyTrait,
    "Hasty": HastyTrait,
    "Inherited": InheritedTrait,
    "Inspiring": InspiringTrait,
    "Nearby": NearbyTrait,
    "Patient": PatientTrait,
    "Pious": PiousTrait,
    "Reckless": RecklessTrait,
    "Rich": RichTrait,
    "Shy": ShyTrait,
    "Tireless": TirelessTrait,
    "Fawning": FawningTrait,
}


def get_trait(name: str) -> Trait:
    """Return a fresh Trait instance by name."""
    if name not in TRAITS:
        raise ValueError(f"Unknown trait: {name}")
    return TRAITS[name]()


def apply_trait(game_state, trait_name: str, target_pile_name: str) -> None:
    """Convenience: instantiate the named trait and bind it to a pile."""
    get_trait(trait_name).apply(game_state, target_pile_name)
