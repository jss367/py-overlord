from ..base_card import Card, CardCost, CardStats, CardType


class RiverShrine(Card):
    """Action-Omen ($4): +1 Sun.
    Trash up to 2 cards from your hand. At the start of Clean-up, if you
    didn't gain any cards in your Buy phase this turn, gain a card costing
    up to $4.
    """

    def __init__(self):
        super().__init__(
            name="River Shrine",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.OMEN],
        )

    def play_effect(self, game_state):
        player = game_state.current_player

        for _ in range(2):
            if not player.hand:
                break
            chosen = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if chosen is None or chosen not in player.hand:
                break
            player.hand.remove(chosen)
            game_state.trash_card(player, chosen)

    def on_cleanup_start(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if getattr(player, "cards_gained_this_buy_phase", 0) > 0:
            return

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.debt > 0 or card.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, card) > 4:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        chosen = player.ai.choose_buy(game_state, candidates + [None])
        if chosen is None:
            return
        if game_state.supply.get(chosen.name, 0) <= 0:
            return
        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
