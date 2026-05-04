from ..base_card import Card, CardCost, CardStats, CardType


class Smugglers(Card):
    """Action ($3): Gain a copy of a card costing up to $6 that the player to your
    right gained on their last turn.
    """

    def __init__(self):
        super().__init__(
            name="Smugglers",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        player_idx = game_state.players.index(player)

        # "Right" in Dominion = the previous player in turn order (turns
        # proceed clockwise / "to the left"), so the right neighbor's last
        # turn is the one that just finished before ours.
        right_idx = (player_idx - 1) % len(game_state.players)
        right_player = game_state.players[right_idx]

        # Find candidates from the right neighbor's last turn gains.
        last_gains = list(getattr(right_player, "gained_cards_last_turn", []))
        if not last_gains:
            return

        candidates = []
        for name in last_gains:
            if game_state.supply.get(name, 0) <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins > 6:
                continue
            if card.cost.potions > 0:
                continue
            if card.cost.debt > 0:
                continue
            candidates.append(card)

        if not candidates:
            return

        choice = player.ai.choose_smugglers_target(game_state, player, candidates)
        if choice is None:
            return

        if game_state.supply.get(choice.name, 0) <= 0:
            return

        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, get_card(choice.name))
