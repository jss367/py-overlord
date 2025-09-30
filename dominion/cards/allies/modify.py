from ..base_card import Card, CardCost, CardStats, CardType


class Modify(Card):
    def __init__(self):
        super().__init__(
            name="Modify",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if not player.hand:
            return
        to_trash = player.ai.choose_card_to_trash(game_state, player.hand)
        if to_trash is None or to_trash not in player.hand:
            to_trash = min(player.hand, key=lambda card: (card.cost.coins, card.name))

        if to_trash not in player.hand:
            return

        player.hand.remove(to_trash)
        game_state.trash_card(player, to_trash)

        max_cost = to_trash.cost.coins + 2
        gainable_cards = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            candidate = get_card(name)
            if candidate.cost.coins <= max_cost:
                gainable_cards.append(candidate)

        chosen_gain = None
        if gainable_cards:
            choice = player.ai.choose_buy(game_state, gainable_cards + [None])
            if choice is not None:
                chosen_gain = choice

        if chosen_gain is None:
            if not player.ignore_action_bonuses:
                player.actions += 1
            game_state.draw_cards(player, 1)
        else:
            if game_state.supply.get(chosen_gain.name, 0) <= 0:
                return
            game_state.supply[chosen_gain.name] -= 1
            game_state.gain_card(player, chosen_gain)
