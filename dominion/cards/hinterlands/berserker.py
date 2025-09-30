from ..base_card import Card, CardCost, CardStats, CardType


class Berserker(Card):
    def __init__(self):
        super().__init__(
            name="Berserker",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        gained = self._gain_cheaper_card(game_state, player)
        self._attack_others(game_state, player)

        return gained

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if any(card.is_action for card in player.in_play):
            self._play_now(game_state, player)

    def _gain_cheaper_card(self, game_state, player):
        from ..registry import get_card

        options = [
            get_card(name)
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins < self.cost.coins
        ]

        if not options:
            return None

        choice = player.ai.choose_buy(game_state, options + [None])
        if not choice:
            choice = max(options, key=lambda card: (card.cost.coins, card.name))

        if game_state.supply.get(choice.name, 0) <= 0:
            return None

        game_state.supply[choice.name] -= 1
        return game_state.gain_card(player, choice)

    def _attack_others(self, game_state, player):
        def discard_priority(card):
            if card.name == "Curse":
                return (0, card.name)
            if card.is_victory and not card.is_action:
                return (1, card.cost.coins, card.name)
            if card.name == "Copper":
                return (2, card.name)
            if card.is_treasure:
                return (3, card.cost.coins, card.name)
            return (4, card.cost.coins, card.name)

        for other in game_state.players:
            if other is player:
                continue

            while len(other.hand) > 3:
                to_discard = min(other.hand, key=discard_priority)
                other.hand.remove(to_discard)
                game_state.discard_card(other, to_discard)

    def _play_now(self, game_state, player):
        if self in player.discard:
            player.discard.remove(self)
        elif self in player.deck:
            player.deck.remove(self)
        elif self in player.hand:
            player.hand.remove(self)
        elif self in game_state.trash:
            game_state.trash.remove(self)
        else:
            return

        player.in_play.append(self)
        self.on_play(game_state)
