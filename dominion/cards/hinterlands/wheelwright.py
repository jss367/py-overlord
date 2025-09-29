from ..base_card import Card, CardCost, CardStats, CardType


class Wheelwright(Card):
    def __init__(self):
        super().__init__(
            name="Wheelwright",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return

        choice = self._choose_discard(player, game_state)
        if not choice:
            return

        player.hand.remove(choice)
        game_state.discard_card(player, choice)

        options = [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).is_action and get_card(name).cost.coins <= choice.cost.coins
        ]

        if not options:
            return

        gain_choice = player.ai.choose_buy(game_state, options + [None])
        if not gain_choice:
            gain_choice = max(options, key=lambda card: (card.cost.coins, card.name))

        if game_state.supply.get(gain_choice.name, 0) <= 0:
            return

        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, gain_choice)

    @staticmethod
    def _choose_discard(player, game_state):
        # Prefer discarding green or junk cards when an action gain is available
        priority = []
        for card in player.hand:
            if not Wheelwright._can_gain_action(card, game_state):
                continue
            if card.name == "Curse":
                priority.append((0, card))
            elif card.is_victory and not card.is_action:
                priority.append((1, card))
            elif card.name == "Copper":
                priority.append((2, card))
            else:
                priority.append((3, card))

        if not priority:
            return None

        priority.sort(key=lambda item: (item[0], item[1].cost.coins, item[1].name))
        return priority[0][1]

    @staticmethod
    def _can_gain_action(card, game_state):
        from ..registry import get_card

        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.is_action and candidate.cost.coins <= card.cost.coins:
                return True
        return False
