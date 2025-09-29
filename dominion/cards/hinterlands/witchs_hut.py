from ..base_card import Card, CardCost, CardStats, CardType


class WitchsHut(Card):
    def __init__(self):
        super().__init__(
            name="Witch's Hut",
            cost=CardCost(coins=5),
            stats=CardStats(cards=4),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return

        discards = sorted(player.hand, key=self._discard_priority)[:2]
        actions_discarded = len(discards) == 2 and all(card.is_action for card in discards)

        for card in discards:
            if card in player.hand:
                player.hand.remove(card)
                game_state.discard_card(player, card)

        if actions_discarded:
            for other in game_state.players:
                if other is player:
                    continue

                def give_curse(target, _game_state=game_state):
                    _game_state.give_curse_to_player(target)

                game_state.attack_player(other, give_curse)

    @staticmethod
    def _discard_priority(card):
        if card.name == "Curse":
            return (0, card.name)
        if not card.is_action and card.is_victory:
            return (1, card.cost.coins, card.name)
        if card.name == "Copper":
            return (2, card.name)
        return (3, card.cost.coins, card.name)
