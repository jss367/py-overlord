"""Implementation of the Steward choice card."""

from ..base_card import Card, CardCost, CardStats, CardType


class Steward(Card):
    def __init__(self):
        super().__init__(
            name="Steward",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        choice = self._choose_option(player)

        if choice == "cards":
            game_state.draw_cards(player, 2)
        elif choice == "coins":
            player.coins += 2
        elif choice == "trash":
            self._trash_up_to_two_cards(game_state, player)

    def _choose_option(self, player) -> str:
        junk = [card for card in player.hand if self._is_junk(card)]
        if junk:
            return "trash"

        if player.coins < 4:
            return "coins"

        return "cards"

    def _trash_up_to_two_cards(self, game_state, player):
        if not player.hand:
            return

        selections = player.ai.choose_cards_to_trash(game_state, list(player.hand), 2)
        trashed = 0

        for card in selections[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
                trashed += 1

        while trashed < 2:
            candidate = self._find_trash_candidate(player.hand)
            if not candidate:
                break
            player.hand.remove(candidate)
            game_state.trash_card(player, candidate)
            trashed += 1

    @staticmethod
    def _find_trash_candidate(cards):
        if not cards:
            return None
        return min(cards, key=Steward._trash_priority)

    @staticmethod
    def _is_junk(card):
        if card.name == "Curse":
            return True
        if card.name == "Copper":
            return True
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return True
        return False

    @staticmethod
    def _trash_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action and card.cost.coins <= 2:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
