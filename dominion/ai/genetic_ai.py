from typing import TYPE_CHECKING, Optional

from dominion.ai.base_ai import AI
from dominion.cards.base_card import Card
from dominion.strategy.enhanced_strategy import EnhancedStrategy

if TYPE_CHECKING:  # Avoid circular imports at runtime
    from dominion.game.game_state import GameState


class GeneticAI(AI):
    """AI that uses a learnable strategy with improved heuristics."""

    def __init__(self, strategy: EnhancedStrategy):
        self.strategy = strategy
        self._name = f"GeneticAI-{id(self)}"

    @property
    def name(self) -> str:
        return self._name

    def choose_action(self, state: "GameState", choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        strategy_choices = (
            valid_choices
            if getattr(state, "_choosing_main_action_phase", False)
            else choices
        )
        return self.strategy.choose_action(state, state.current_player, strategy_choices)

    def choose_treasure(self, state: "GameState", choices: list[Optional[Card]]) -> Optional[Card]:
        valid_choices = [c for c in choices if c is not None]
        if not valid_choices:
            return None

        return self.strategy.choose_treasure(state, state.current_player, valid_choices)

    def choose_buy(self, state: "GameState", choices: list[Optional[Card]]) -> Optional[Card]:
        if not choices:
            return None

        return self.strategy.choose_gain(state, state.current_player, choices)

    def choose_mastermind_action(self, state, player, choices):
        hook = getattr(self.strategy, "choose_mastermind_action", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_mastermind_action(state, player, choices)

    def choose_coffers_for_debt(self, state, player, maximum):
        hook = getattr(self.strategy, "choose_coffers_for_debt", None)
        if hook is not None:
            return hook(state, player, maximum)
        return super().choose_coffers_for_debt(state, player, maximum)

    def choose_mine_treasure(self, state, player, choices):
        hook = getattr(self.strategy, "choose_mine_treasure", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_mine_treasure(state, player, choices)

    def choose_mine_gain(self, state, player, choices):
        hook = getattr(self.strategy, "choose_mine_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_mine_gain(state, player, choices)

    def choose_kind_emperor_gain(self, state, player, choices):
        hook = getattr(self.strategy, "choose_kind_emperor_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_kind_emperor_gain(state, player, choices)

    def choose_anvil_gain(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        """Use an Anvil-specific policy when supplied, else the gain menu."""
        hook = getattr(self.strategy, "choose_anvil_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return self.strategy.choose_gain(state, player, choices)

    def choose_anvil_treasure_to_discard(self, state, player, choices):
        hook = getattr(self.strategy, "choose_anvil_treasure_to_discard", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_anvil_treasure_to_discard(state, player, choices)

    # ---- Bilbao board hooks (Grotto / Shaman / Hermit / Wheelwright / ...) ----

    def choose_cards_to_set_aside_for_grotto(self, state, player, hand):
        hook = getattr(self.strategy, "choose_grotto_set_aside", None)
        if hook is not None:
            return hook(state, player, hand)
        return super().choose_cards_to_set_aside_for_grotto(state, player, hand)

    def choose_card_to_gain_from_trash_with_shaman(self, state, player, choices):
        """Strategy hook first, then the gain menu, then the safe default."""
        hook = getattr(self.strategy, "choose_shaman_gain", None)
        if hook is not None:
            pick = hook(state, player, choices)
            if pick is not None:
                return pick
        pick = self.strategy.choose_gain(state, player, choices)
        if pick is not None:
            return pick
        return super().choose_card_to_gain_from_trash_with_shaman(state, player, choices)

    def should_trash_fools_gold_for_gold(self, state, player):
        hook = getattr(self.strategy, "should_trash_fools_gold_for_gold", None)
        if hook is not None:
            return bool(hook(state, player))
        return super().should_trash_fools_gold_for_gold(state, player)

    def choose_wheelwright_discard(self, state, player, hand):
        hook = getattr(self.strategy, "choose_wheelwright_discard", None)
        if hook is not None:
            return hook(state, player, hand)
        return super().choose_wheelwright_discard(state, player, hand)

    def should_trash_with_hermit(self, state, player, choices):
        """Hermit's optional trash follows the strategy's trash list."""
        hook = getattr(self.strategy, "should_trash_with_hermit", None)
        if hook is not None:
            return hook(state, player, choices)
        return self.strategy.choose_trash(state, player, choices)

    def choose_card_to_gain_with_hermit(self, state, player, choices):
        """Hermit's mandatory $0-$3 gain follows the gain menu when it wants
        something; otherwise the generic default (best Action) applies."""
        hook = getattr(self.strategy, "choose_hermit_gain", None)
        if hook is not None:
            pick = hook(state, player, choices)
            if pick is not None:
                return pick
        pick = self.strategy.choose_gain(state, player, choices)
        if pick is not None:
            return pick
        return super().choose_card_to_gain_with_hermit(state, player, choices)

    def should_play_sheepdog(self, state, player, gained_card):
        hook = getattr(self.strategy, "should_play_sheepdog", None)
        if hook is not None:
            return bool(hook(state, player, gained_card))
        return super().should_play_sheepdog(state, player, gained_card)

    def should_play_falconer(self, state: "GameState", player, gainer, gained_card):
        hook = getattr(self.strategy, "should_play_falconer", None)
        if hook is not None:
            return bool(hook(state, player, gainer, gained_card))
        return super().should_play_falconer(state, player, gainer, gained_card)

    def choose_card_to_trash_for_knight_attack(self, state, player, choices):
        hook = getattr(self.strategy, "choose_card_to_trash_for_knight_attack", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_trash_for_knight_attack(state, player, choices)

    def choose_card_to_trash_for_rogue_attack(self, state, player, choices):
        hook = getattr(self.strategy, "choose_card_to_trash_for_rogue_attack", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_trash_for_rogue_attack(state, player, choices)

    def choose_treasure_to_discard_for_stables(self, state, player, choices):
        hook = getattr(self.strategy, "choose_treasure_to_discard_for_stables", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_treasure_to_discard_for_stables(state, player, choices)

    def choose_treasure_to_trash_for_spice_merchant(self, state, player, choices):
        hook = getattr(self.strategy, "choose_treasure_to_trash_for_spice_merchant", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_treasure_to_trash_for_spice_merchant(state, player, choices)

    def choose_spice_merchant_mode(self, state, player):
        hook = getattr(self.strategy, "choose_spice_merchant_mode", None)
        if hook is not None:
            return hook(state, player)
        return super().choose_spice_merchant_mode(state, player)

    def choose_armory_gain(self, state, player, choices):
        hook = getattr(self.strategy, "choose_armory_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_armory_gain(state, player, choices)

    def choose_artificer_gain(self, state, player, choices):
        hook = getattr(self.strategy, "choose_artificer_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_artificer_gain(state, player, choices)

    def choose_card_to_topdeck_for_scheme(self, state, player, choices):
        hook = getattr(self.strategy, "choose_card_to_topdeck_for_scheme", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_topdeck_for_scheme(state, player, choices)

    def choose_quartermaster_option(self, state: "GameState", player, mat, candidates):
        hook = getattr(self.strategy, "choose_quartermaster_option", None)
        if hook is not None:
            return hook(state, player, mat, candidates)
        return super().choose_quartermaster_option(state, player, mat, candidates)

    def choose_courier_target(self, state, player, choices: list[Card]) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_courier_target", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_courier_target(state, player, choices)

    def choose_overlord_target(self, state, player, choices: list[Card]) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_overlord_target", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_overlord_target(state, player, choices)

    def choose_quartermaster_gain(self, state, player, choices: list[Card]) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_quartermaster_gain", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_quartermaster_gain(state, player, choices)

    def quartermaster_take_all(self, state, player, mat: list[Card]) -> bool:
        hook = getattr(self.strategy, "quartermaster_take_all", None)
        if hook is not None:
            return bool(hook(state, player, mat))
        return super().quartermaster_take_all(state, player, mat)

    def choose_way(self, state: "GameState", card: Card, ways: list) -> Optional[object]:
        if hasattr(self.strategy, 'choose_way'):
            return self.strategy.choose_way(state, state.current_player, card, ways)
        return None

    def choose_torturer_attack(self, state: "GameState", player) -> bool:
        if hasattr(self.strategy, 'choose_torturer_response'):
            return self.strategy.choose_torturer_response(state, player)
        return super().choose_torturer_attack(state, player)

    def choose_card_to_trash(self, state: "GameState", choices: list[Card]) -> Optional[Card]:
        if not choices:
            return None

        return self.strategy.choose_trash(state, state.current_player, choices)

    def choose_card_to_exile_for_bounty_hunter(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        """Use the strategy's Bounty Hunter order before the generic policy."""
        choice = self.strategy.choose_bounty_hunter_exile(state, player, choices)
        if choice is not None:
            return choice
        return super().choose_card_to_exile_for_bounty_hunter(
            state, player, choices
        )

    def choose_watchtower_reaction(
        self, state: "GameState", player, gained_card: Card
    ) -> Optional[str]:
        hook = getattr(self.strategy, "choose_watchtower_reaction", None)
        if hook is not None:
            return hook(state, player, gained_card)
        return super().choose_watchtower_reaction(state, player, gained_card)

    def choose_card_to_topdeck_for_clerk(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_card_to_topdeck_for_clerk", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_topdeck_for_clerk(state, player, choices)

    def should_play_clerk_reaction(
        self, state: "GameState", player, clerk: Card | None = None
    ) -> bool:
        hook = getattr(self.strategy, "should_play_clerk_reaction", None)
        if hook is not None:
            return bool(hook(state, player, clerk))
        return super().should_play_clerk_reaction(state, player, clerk)

    def choose_investment_mode(
        self, state: "GameState", player, can_trash_treasure: bool
    ) -> str:
        hook = getattr(self.strategy, "choose_investment_mode", None)
        if hook is not None:
            return hook(state, player, can_trash_treasure)
        return super().choose_investment_mode(state, player, can_trash_treasure)

    def choose_treasure_to_trash_for_investment(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_treasure_to_trash_for_investment", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_treasure_to_trash_for_investment(state, player, choices)

    # ------------------------------------------------------------------
    # Generic strategy-level overrides for per-card decisions. A strategy may
    # define any of these methods (same signature as the AI hook, minus
    # ``self``) to replace the tactical default.
    # ------------------------------------------------------------------
    def choose_steward_mode(self, state: "GameState", player) -> str:
        hook = getattr(self.strategy, "choose_steward_mode", None)
        if hook is not None:
            return hook(state, player)
        return super().choose_steward_mode(state, player)

    def choose_card_to_pass_for_masquerade(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_card_to_pass_for_masquerade", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_card_to_pass_for_masquerade(state, player, choices)

    def should_play_cultist_chain(self, state: "GameState", player) -> bool:
        hook = getattr(self.strategy, "should_play_cultist_chain", None)
        if hook is not None:
            return bool(hook(state, player))
        return super().should_play_cultist_chain(state, player)

    def choose_disciple_action_to_replay(
        self, state: "GameState", player, choices: list[Card]
    ) -> Optional[Card]:
        hook = getattr(self.strategy, "choose_disciple_action_to_replay", None)
        if hook is not None:
            return hook(state, player, choices)
        return super().choose_disciple_action_to_replay(state, player, choices)

    def should_exchange_traveller(self, state: "GameState", player, card: Card) -> bool:
        hook = getattr(self.strategy, "should_exchange_traveller", None)
        if hook is not None:
            return bool(hook(state, player, card))
        return super().should_exchange_traveller(state, player, card)

    def choose_teacher_token(self, state: "GameState", player, options: list[str]) -> str:
        hook = getattr(self.strategy, "choose_teacher_token", None)
        if hook is not None:
            return hook(state, player, options)
        return super().choose_teacher_token(state, player, options)

    def choose_cards_to_discard(
        self, state: "GameState", player, choices: list[Card], count: int, *, reason=None
    ) -> list[Card]:
        hook = getattr(self.strategy, "choose_cards_to_discard", None)
        if hook is not None:
            return hook(state, player, choices, count, reason=reason)
        return super().choose_cards_to_discard(state, player, choices, count, reason=reason)
