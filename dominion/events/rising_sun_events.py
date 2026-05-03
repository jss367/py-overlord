"""Events from the Rising Sun expansion."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Amass(Event):
    """$2: If you have no Action cards in play, gain an Action card costing
    up to $5.
    """

    def __init__(self):
        super().__init__("Amass", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        # Per rulebook: Duration cards in play that were played on previous
        # turns count too, blocking Amass.
        all_in_play = list(player.in_play) + list(player.duration)
        if any(card.is_action for card in all_in_play):
            return

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not card.is_action:
                continue
            if card.cost.debt > 0 or card.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, card) > 5:
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


class Asceticism(Event):
    """$2 (overpay supported): You may pay any extra amount $X. Trash X cards
    from your hand.
    """

    def __init__(self):
        super().__init__("Asceticism", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        extra = player.ai.choose_asceticism_overpay(
            game_state, player, available=player.coins
        )
        extra = max(0, min(extra, player.coins, len(player.hand)))
        if extra <= 0:
            return
        player.coins -= extra
        player.coins_spent_this_turn += extra

        chosen = player.ai.choose_cards_to_trash(
            game_state, list(player.hand), extra
        )
        chosen = chosen[:extra]
        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)


class Credit(Event):
    """$2: Gain an Action or Treasure card costing up to $8. Take Debt equal
    to its cost.

    Excludes cards whose own cost contains Debt — "up to $X" by definition
    skips them.
    """

    def __init__(self):
        super().__init__("Credit", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if not (card.is_action or card.is_treasure):
                continue
            if card.cost.debt > 0:
                continue
            if card.cost.potions > 0:
                continue
            if game_state.get_card_cost(player, card) > 8:
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
        cost_to_pay = game_state.get_card_cost(player, chosen)
        game_state.supply[chosen.name] -= 1
        game_state.gain_card(player, chosen)
        player.debt += cost_to_pay


class Foresight(Event):
    """$2: Reveal cards from the top of your deck until you reveal an Action.
    Set it aside, discard the rest. The card is added to your hand after
    drawing your next hand.
    """

    def __init__(self):
        super().__init__("Foresight", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        revealed: list = []
        found = None
        while True:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            card = player.deck.pop()
            revealed.append(card)
            if card.is_action:
                found = card
                break

        if found is not None:
            revealed.remove(found)
            player.foresight_set_aside.append(found)

        for card in revealed:
            game_state.discard_card(player, card)


class Gather(Event):
    """$7: Gain a card costing exactly $3, exactly $4, and exactly $5
    (in that order; skip individually if no candidate exists).
    """

    def __init__(self):
        super().__init__("Gather", CardCost(coins=7))

    def on_buy(self, game_state, player) -> None:
        for target_cost in (3, 4, 5):
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
                if game_state.get_card_cost(player, card) != target_cost:
                    continue
                if not card.may_be_bought(game_state):
                    continue
                candidates.append(card)
            if not candidates:
                continue
            chosen = player.ai.choose_buy(game_state, candidates + [None])
            if chosen is None:
                continue
            if game_state.supply.get(chosen.name, 0) <= 0:
                continue
            game_state.supply[chosen.name] -= 1
            game_state.gain_card(player, chosen)


class Kintsugi(Event):
    """$3: Trash a card from your hand. If you've gained a Gold this game,
    gain a card costing up to $2 more than the trashed card.
    """

    def __init__(self):
        super().__init__("Kintsugi", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return
        gained_gold = getattr(player, "kintsugi_has_gained_gold", False)
        chosen = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if chosen is None or chosen not in player.hand:
            return
        trashed_cost = game_state.get_card_cost(player, chosen)
        player.hand.remove(chosen)
        game_state.trash_card(player, chosen)

        if not gained_gold:
            return

        max_cost = trashed_cost + 2
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
            if game_state.get_card_cost(player, card) > max_cost:
                continue
            if not card.may_be_bought(game_state):
                continue
            candidates.append(card)
        if not candidates:
            return
        gain_choice = player.ai.choose_buy(game_state, candidates + [None])
        if gain_choice is None:
            return
        if game_state.supply.get(gain_choice.name, 0) <= 0:
            return
        game_state.supply[gain_choice.name] -= 1
        game_state.gain_card(player, gain_choice)


class Practice(Event):
    """$3: You may play an Action card from your hand twice."""

    def __init__(self):
        super().__init__("Practice", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        actions = [c for c in player.hand if c.is_action]
        if not actions:
            return
        chosen = player.ai.choose_action(game_state, actions + [None])
        if chosen is None or chosen not in player.hand:
            return
        player.hand.remove(chosen)
        player.in_play.append(chosen)
        chosen.on_play(game_state)
        chosen.on_play(game_state)


class ReceiveTribute(Event):
    """$5: If you've gained at least 3 cards this turn, gain up to 3
    differently named Action cards you don't have copies of in play.
    """

    def __init__(self):
        super().__init__("Receive Tribute", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        if getattr(player, "cards_gained_this_turn", 0) < 3:
            return
        in_play_names = {c.name for c in player.in_play + player.duration}
        gained_names: set = set()
        for _ in range(3):
            candidates = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                try:
                    card = get_card(name)
                except ValueError:
                    continue
                if not card.is_action:
                    continue
                if name in in_play_names or name in gained_names:
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
            gained_names.add(chosen.name)


class SeaTrade(Event):
    """$4: +1 Card per Action card you have in play. Trash up to that many
    cards from your hand.
    """

    def __init__(self):
        super().__init__("Sea Trade", CardCost(coins=4))

    def on_buy(self, game_state, player) -> None:
        action_count = sum(
            1 for c in player.in_play + player.duration if c.is_action
        )
        if action_count <= 0:
            return
        game_state.draw_cards(player, action_count)
        if not player.hand:
            return
        chosen = player.ai.choose_cards_to_trash(
            game_state, list(player.hand), action_count
        )
        chosen = chosen[:action_count]
        for card in chosen:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
