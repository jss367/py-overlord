from ..base_card import Card, CardCost, CardStats, CardType


class Butcher(Card):
    """Trash-for-benefit card that uses Coin tokens to upgrade gains."""

    def __init__(self):
        super().__init__(
            name="Butcher",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        player.coin_tokens += 2

        if not player.hand:
            return

        trash_choice = player.ai.choose_card_to_trash(game_state, list(player.hand) + [None])
        if trash_choice is None or trash_choice not in player.hand:
            return

        player.hand.remove(trash_choice)
        game_state.trash_card(player, trash_choice)
        trashed_cost = trash_choice.cost.coins

        gained_first = False
        affordable: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= trashed_cost + 2:
                affordable.append(card)

        if affordable:
            choice = player.ai.choose_buy(game_state, affordable + [None])
            if choice is None:
                choice = max(affordable, key=lambda c: (c.cost.coins, c.stats.vp, c.name))
            if game_state.supply.get(choice.name, 0) > 0:
                game_state.supply[choice.name] -= 1
                game_state.gain_card(player, choice)
                gained_first = True

        if not gained_first or player.coin_tokens <= 0:
            return

        upgrade_options: dict[str, tuple[Card, int]] = {}
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            diff = card.cost.coins - trashed_cost
            if diff < 0 or diff > player.coin_tokens:
                continue
            current = upgrade_options.get(name)
            if current is None or card.cost.coins > current[0].cost.coins:
                upgrade_options[name] = (card, diff)

        if not upgrade_options:
            return

        options = [value[0] for value in upgrade_options.values()]
        choice = player.ai.choose_buy(game_state, options + [None])
        if choice is None:
            choice = max(options, key=lambda c: (c.cost.coins, c.stats.vp, c.name))

        selected = upgrade_options.get(choice.name)
        if not selected:
            return

        card, diff = selected
        if diff > player.coin_tokens or game_state.supply.get(card.name, 0) <= 0:
            return

        player.coin_tokens -= diff
        game_state.supply[card.name] -= 1
        game_state.gain_card(player, card)
