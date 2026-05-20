from ..base_card import CardCost, CardStats, CardType
from ..split_pile import TopSplitPileCard


class Catapult(TopSplitPileCard):
    """Trash a card; opponents gain Curses or discard based on what it was."""

    partner_card_name = "Rocks"

    def __init__(self):
        super().__init__(
            name="Catapult",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        get_cost = getattr(game_state, "get_card_cost", None)

        def card_cost(card):
            return get_cost(player, card) if get_cost is not None else card.cost.coins

        to_trash = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if to_trash is None:
            to_trash = min(player.hand, key=card_cost)
        if to_trash not in player.hand:
            return

        trashed_cost = card_cost(to_trash)
        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        gives_curse = trashed_cost >= 3
        discards_to_three = game_state.is_treasure(to_trash)
        if not gives_curse and not discards_to_three:
            return

        def attack(target):
            if gives_curse:
                game_state.give_curse_to_player(target)

            if not discards_to_three or len(target.hand) <= 3:
                return

            discard_needed = len(target.hand) - 3
            selected = target.ai.choose_cards_to_discard(
                game_state,
                target,
                list(target.hand),
                discard_needed,
                reason="catapult",
            )
            for card in selected[:discard_needed]:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

            while len(target.hand) > 3:
                card = min(target.hand, key=self._discard_priority)
                target.hand.remove(card)
                game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack, attacker=player, attack_card=self)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.cost.coins, card.name)
        if card.is_victory and not card.is_action:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.cost.coins, card.name)
        return (3, card.cost.coins, card.name)
