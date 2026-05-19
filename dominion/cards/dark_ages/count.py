"""Implementation of the Count card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Count(Card):
    """Choose one of three first effects, then one of three second effects."""

    def __init__(self):
        super().__init__(
            name="Count",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        self._resolve_first_choice(game_state, player)
        self._resolve_second_choice(game_state, player)

    def _resolve_first_choice(self, game_state, player):
        choice = self._choose_first_mode(game_state, player)

        if choice == "discard":
            self._discard_two(game_state, player)
        elif choice == "topdeck":
            self._topdeck_from_hand(game_state, player)
        elif choice == "copper":
            self._gain_from_supply(game_state, player, "Copper")

    def _resolve_second_choice(self, game_state, player):
        choice = self._choose_second_mode(game_state, player)

        if choice == "coins":
            player.coins += 3
        elif choice == "trash":
            for card in list(player.hand):
                player.hand.remove(card)
                game_state.trash_card(player, card)
        elif choice == "duchy":
            self._gain_from_supply(game_state, player, "Duchy")

    def _choose_first_mode(self, game_state, player):
        options = ["discard", "topdeck"]
        if game_state.supply.get("Copper", 0) > 0:
            options.append("copper")

        hook = getattr(player.ai, "choose_count_first_mode", None)
        if hook is None:
            hook = getattr(player.ai, "choose_count_first_choice", None)
        if hook is not None:
            choice = hook(game_state, player, list(options))
            if choice in options:
                return choice

        discardable = [card for card in player.hand if self._is_disposable(card)]
        if len(discardable) >= 2:
            return "discard"
        if player.hand:
            return "topdeck"
        if "copper" in options:
            return "copper"
        return "discard"

    def _choose_second_mode(self, game_state, player):
        options = ["coins", "trash"]
        if game_state.supply.get("Duchy", 0) > 0:
            options.append("duchy")

        hook = getattr(player.ai, "choose_count_second_mode", None)
        if hook is None:
            hook = getattr(player.ai, "choose_count_second_choice", None)
        if hook is not None:
            choice = hook(game_state, player, list(options))
            if choice in options:
                return choice

        if "duchy" in options and game_state.turn_number >= 10:
            return "duchy"
        if player.hand and all(self._is_disposable(card) for card in player.hand):
            return "trash"
        return "coins"

    def _discard_two(self, game_state, player):
        if not player.hand:
            return

        choices = list(player.hand)
        selected = player.ai.choose_cards_to_discard(
            game_state, player, choices, 2, reason="count"
        )
        selected = self._valid_unique_cards(selected, choices)

        remaining = [card for card in choices if card not in selected]
        while len(selected) < min(2, len(choices)) and remaining:
            fallback = min(remaining, key=self._discard_priority)
            selected.append(fallback)
            remaining.remove(fallback)

        for card in selected[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

    def _topdeck_from_hand(self, game_state, player):
        if not player.hand:
            return

        choices = list(player.hand)
        choice = player.ai.choose_card_to_topdeck_from_hand(
            game_state, player, choices, reason="count"
        )
        if choice not in choices:
            choice = min(choices, key=self._topdeck_priority)

        player.hand.remove(choice)
        player.deck.append(choice)

    def _gain_from_supply(self, game_state, player, card_name):
        if game_state.supply.get(card_name, 0) <= 0:
            return

        from ..registry import get_card

        game_state.supply[card_name] -= 1
        game_state.gain_card(player, get_card(card_name))

    @staticmethod
    def _valid_unique_cards(selected, choices):
        valid = []
        remaining = list(choices)
        if selected is None:
            candidates = []
        elif isinstance(selected, (list, tuple)):
            candidates = selected
        else:
            candidates = [selected]

        for card in candidates:
            if card in remaining:
                valid.append(card)
                remaining.remove(card)
        return valid

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, 0, card.name)
        if card.name == "Estate":
            return (1, 0, card.name)
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, 0, card.name)
        return (3, card.cost.coins, card.name)

    @staticmethod
    def _topdeck_priority(card):
        if card.is_action:
            return (0, -card.cost.coins, card.name)
        if card.is_treasure:
            return (1, -card.cost.coins, card.name)
        return (2, card.cost.coins, card.name)

    @staticmethod
    def _is_disposable(card):
        if card.name in {"Curse", "Copper", "Estate", "Hovel", "Overgrown Estate"}:
            return True
        if card.is_ruins:
            return True
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return True
        return False
