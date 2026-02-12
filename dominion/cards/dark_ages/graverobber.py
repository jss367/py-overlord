from ..base_card import Card, CardCost, CardStats, CardType


class Graverobber(Card):
    def __init__(self):
        super().__init__(
            name="Graverobber",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        options = []
        trash_candidates = [
            c for c in game_state.trash
            if 3 <= game_state.get_card_cost(player, c) <= 6
        ]
        if trash_candidates:
            options.append("gain_from_trash")
        action_in_hand = [c for c in player.hand if c.is_action]
        if action_in_hand:
            options.append("upgrade")
        if not options:
            return
        mode = player.ai.choose_graverobber_mode(game_state, player, options)
        if mode not in options:
            mode = options[0]
        if mode == "gain_from_trash":
            self._gain_from_trash(game_state, player, trash_candidates)
        else:
            self._upgrade(game_state, player, action_in_hand)

    def _gain_from_trash(self, game_state, player, candidates):
        from ..registry import get_card
        choice = player.ai.choose_buy(game_state, candidates + [None])
        if not choice or choice not in candidates:
            choice = candidates[0]
        game_state.trash.remove(choice)
        player.deck.insert(0, choice)

    def _upgrade(self, game_state, player, action_cards):
        from ..registry import get_card
        choice = player.ai.choose_card_to_trash(game_state, action_cards)
        if not choice or choice not in action_cards:
            choice = action_cards[0]
        trashed_cost = game_state.get_card_cost(player, choice)
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        max_cost = trashed_cost + 3
        gain_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if game_state.get_card_cost(player, card) <= max_cost:
                gain_options.append(card)
        if not gain_options:
            return
        gain_choice = player.ai.choose_buy(game_state, gain_options + [None])
        if not gain_choice or gain_choice not in gain_options:
            gain_choice = max(gain_options, key=lambda c: (c.cost.coins, c.name))
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, gain_choice)
