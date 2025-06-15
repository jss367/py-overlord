from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card
from .base_event import Event


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
    """Trash a card to gain one costing up to 3 more."""

    def __init__(self):
        super().__init__("Enhance", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return
        card = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if not card:
            return
        player.hand.remove(card)
        game_state.trash_card(player, card)
        max_cost = card.cost.coins + 3
        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= max_cost
        ]
        if affordable:
            gain = get_card(affordable[0])
            game_state.supply[gain.name] -= 1
            player.discard.append(gain)
            gain.on_gain(game_state, player)


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
