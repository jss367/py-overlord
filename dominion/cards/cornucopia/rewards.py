from ..base_card import Card, CardCost, CardStats, CardType


class Coronet(Card):
    def __init__(self):
        super().__init__(
            name="Coronet",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        playable = [
            c for c in player.hand
            if (c.is_action and not c.is_duration) or (c.is_treasure and not c.is_duration)
        ]
        if not playable:
            return
        choice = None
        actions = [c for c in playable if c.is_action]
        treasures = [c for c in playable if c.is_treasure]
        if actions:
            choice = player.ai.choose_action(game_state, actions + [None])
        if not choice and treasures:
            choice = player.ai.choose_treasure(game_state, treasures + [None])
        if choice and choice in player.hand:
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(game_state)
            choice.on_play(game_state)


class Demesne(Card):
    def __init__(self):
        super().__init__(
            name="Demesne",
            cost=CardCost(coins=0),
            stats=CardStats(actions=2),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


class Housecarl(Card):
    def __init__(self):
        super().__init__(
            name="Housecarl",
            cost=CardCost(coins=0),
            stats=CardStats(actions=1, cards=3),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:
        return False


class HugeTurnip(Card):
    def __init__(self):
        super().__init__(
            name="Huge Turnip",
            cost=CardCost(coins=0),
            stats=CardStats(coins=2, buys=1),
            types=[CardType.TREASURE],
        )

    def may_be_bought(self, game_state) -> bool:
        return False


class Renown(Card):
    def __init__(self):
        super().__init__(
            name="Renown",
            cost=CardCost(coins=0),
            stats=CardStats(buys=1),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        player.cost_reduction += 2
