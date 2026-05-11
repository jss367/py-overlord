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
            for _ in range(2):
                if choice.is_action:
                    game_state.play_action_indirectly(player, choice)
                else:
                    choice.on_play(game_state)
                    game_state.fire_ally_play_hooks(player, choice)


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


class Courser(Card):
    """Choose two: +2 Cards; +2 Actions; +$2; gain 4 Silvers. The choices
    must be different. (Cornucopia & Guilds 2E Joust Reward.)"""

    OPTIONS = ("cards", "actions", "coins", "silvers")

    def __init__(self):
        super().__init__(
            name="Courser",
            cost=CardCost(coins=0),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        chooser = getattr(player.ai, "choose_courser_options", None)
        if chooser is None:
            chosen = {"cards", "actions"}
        else:
            raw = list(chooser(game_state, player, list(self.OPTIONS)))
            chosen = set()
            for opt in raw:
                if opt in self.OPTIONS and opt not in chosen:
                    chosen.add(opt)
                if len(chosen) == 2:
                    break
            # Fill any missing picks (AI returned fewer than 2 distinct
            # valid options) with the first remaining options in printed
            # order. The choices must be different.
            for opt in self.OPTIONS:
                if len(chosen) == 2:
                    break
                chosen.add(opt)

        # Resolve in printed order regardless of AI selection order.
        for opt in self.OPTIONS:
            if opt not in chosen:
                continue
            if opt == "cards":
                game_state.draw_cards(player, 2)
            elif opt == "actions":
                player.actions += 2
            elif opt == "coins":
                player.coins += 2
            elif opt == "silvers":
                for _ in range(4):
                    if game_state.supply.get("Silver", 0) <= 0:
                        break
                    game_state.supply["Silver"] -= 1
                    game_state.gain_card(player, get_card("Silver"))
