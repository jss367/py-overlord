from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from .base_event import Event


HORSE_PILE_COUNT = 30


def ensure_horse_pile(game_state) -> None:
    """Ensure the shared Horse pile exists in the supply."""

    if "Horse" not in game_state.supply:
        game_state.supply["Horse"] = HORSE_PILE_COUNT


class Desperation(Event):
    """+1 Buy, gain a Curse."""

    def __init__(self):
        super().__init__("Desperation", CardCost(coins=0))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        game_state.give_curse_to_player(player)


class Gamble(Event):
    """Reveal the top card of your deck and play it if possible."""

    def __init__(self):
        super().__init__("Gamble", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        if not player.deck and player.discard:
            player.shuffle_discard_into_deck()
        if player.deck:
            card = player.deck.pop()
            player.in_play.append(card)
            card.on_play(game_state)
        else:
            pass


class March(Event):
    """Play an Action from your discard pile."""

    def __init__(self):
        super().__init__("March", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        actions = [c for c in player.discard if c.is_action]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice:
            player.discard.remove(choice)
            player.in_play.append(choice)
            choice.on_play(game_state)


class Toil(Event):
    """Play an Action from your hand."""

    def __init__(self):
        super().__init__("Toil", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        choice = player.ai.choose_action(game_state, actions + [None])
        if choice:
            player.hand.remove(choice)
            player.in_play.append(choice)
            choice.on_play(game_state)


class Enhance(Event):
    """Trash a non-Victory card to gain one costing up to 2 more."""

    def __init__(self):
        super().__init__("Enhance", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return
        card = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if not card or card.is_victory:
            return
        player.hand.remove(card)
        game_state.trash_card(player, card)
        max_cost = card.cost.coins + 2
        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= max_cost
        ]
        if affordable:
            affordable.sort(key=lambda name: (get_card(name).cost.coins, name), reverse=True)
            gain = get_card(affordable[0])
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)


class Delay(Event):
    """Set aside a card to take next turn."""

    def __init__(self):
        super().__init__("Delay", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return
        choice = player.ai.choose_action(game_state, player.hand + [None])
        if choice:
            player.hand.remove(choice)
            player.delayed_cards.append(choice)


class SeizeTheDay(Event):
    """Take an extra turn (once per game)."""

    def __init__(self):
        super().__init__("Seize the Day", CardCost(coins=4))

    def may_be_bought(self, game_state, player) -> bool:
        return not player.seize_the_day_used

    def on_buy(self, game_state, player) -> None:
        player.seize_the_day_used = True
        player.turns_taken += 1
        game_state.extra_turn = True


class Ride(Event):
    """+1 Buy, gain a Horse if available."""

    def __init__(self):
        super().__init__("Ride", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1

        try:
            horse = get_card("Horse")
        except ValueError:
            return

        ensure_horse_pile(game_state)
        if game_state.supply.get("Horse", 0) > 0:
            game_state.supply["Horse"] -= 1

        game_state.gain_card(player, horse)


class Banish(Event):
    """Exile any number of cards with the same name from your hand."""

    def __init__(self):
        super().__init__("Banish", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return

        grouped: dict[str, list] = {}
        for card in player.hand:
            grouped.setdefault(card.name, []).append(card)

        # Choose the card name with the most copies to provide a reasonable default
        target_name = max(grouped.items(), key=lambda item: (len(item[1]), item[0]))[0]
        to_exile = grouped[target_name]

        for card in to_exile:
            player.hand.remove(card)
            player.exile.append(card)


class Bargain(Event):
    """Gain a non-Victory costing up to 5; other players gain Horses."""

    def __init__(self):
        super().__init__("Bargain", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        supply_cards = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if not card.is_victory and card.cost.coins <= 5:
                supply_cards.append(card)

        if supply_cards:
            supply_cards.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            gain = supply_cards[0]
            game_state.supply[gain.name] -= 1
            game_state.gain_card(player, gain)

        ensure_horse_pile(game_state)
        for other in game_state.players:
            if other is player:
                continue
            if game_state.supply.get("Horse", 0) <= 0:
                break
            game_state.supply["Horse"] -= 1
            horse = get_card("Horse")
            game_state.gain_card(other, horse)


class Invest(Event):
    """Exile an Action card from the Supply; others draw when they gain it."""

    def __init__(self):
        super().__init__("Invest", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        available = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_action:
                available.append(card)

        if not available:
            return

        available.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        chosen = available[0]
        game_state.supply[chosen.name] -= 1
        player.exile.append(chosen)
        player.invested_exile.append(chosen)
        game_state.notify_invest(chosen.name, player)


class Populate(Event):
    """Gain one of each Action card from the Supply."""

    def __init__(self):
        super().__init__("Populate", CardCost(coins=10))

    def on_buy(self, game_state, player) -> None:
        action_names = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_action:
                action_names.append(name)

        for name in action_names:
            if game_state.supply.get(name, 0) <= 0:
                continue
            game_state.supply[name] -= 1
            gained = get_card(name)
            game_state.gain_card(player, gained)


class Stampede(Event):
    """Gain 5 Horses if your hand is empty."""

    def __init__(self):
        super().__init__("Stampede", CardCost(coins=5))

    def may_be_bought(self, game_state, player) -> bool:
        return len(player.hand) == 0

    def on_buy(self, game_state, player) -> None:
        ensure_horse_pile(game_state)
        for _ in range(5):
            if game_state.supply.get("Horse", 0) <= 0:
                break
            game_state.supply["Horse"] -= 1
            horse = get_card("Horse")
            game_state.gain_card(player, horse)


class Transport(Event):
    """Move an Action to or from Exile."""

    def __init__(self):
        super().__init__("Transport", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        exiled_actions = [card for card in player.exile if card.is_action]
        if exiled_actions:
            card = exiled_actions[0]
            player.exile.remove(card)
            if card in player.invested_exile:
                player.invested_exile.remove(card)
            player.deck.insert(0, card)
            return

        available = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.is_action:
                available.append(card)

        if not available:
            return

        available.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        chosen = available[0]
        game_state.supply[chosen.name] -= 1
        player.exile.append(chosen)
