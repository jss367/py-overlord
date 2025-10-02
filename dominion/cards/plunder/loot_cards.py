from ..base_card import Card, CardCost, CardStats, CardType


class Loot(Card):
    """Base class for Loot treasures."""

    def __init__(self, name: str, stats: CardStats):
        super().__init__(
            name=name,
            cost=CardCost(coins=7),
            stats=stats,
            types=[CardType.TREASURE],
        )

    def may_be_bought(self, game_state) -> bool:  # pragma: no cover - not in supply
        return False


class Amphora(Loot):
    def __init__(self):
        super().__init__("Amphora", CardStats())
        self.types.append(CardType.DURATION)
        self.delayed = False

    def play_effect(self, game_state):
        player = game_state.current_player
        use_now = True
        if hasattr(player.ai, "use_amphora_now"):
            use_now = player.ai.use_amphora_now(game_state)
        if use_now:
            player.coins += 3
            player.buys += 1
        else:
            self.delayed = True
            player.duration.append(self)

    def on_duration(self, game_state):
        if self.delayed:
            player = game_state.current_player
            player.coins += 3
            player.buys += 1


class Doubloons(Loot):
    def __init__(self):
        super().__init__("Doubloons", CardStats(coins=3))

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Gold", 0) > 0:
            from ..registry import get_card

            game_state.supply["Gold"] -= 1
            gold = get_card("Gold")
            game_state.gain_card(player, gold)


class EndlessChalice(Loot):
    def __init__(self):
        super().__init__("Endless Chalice", CardStats(coins=1, buys=1))
        self.types.append(CardType.DURATION)
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        player.buys += 1


class Figurehead(Loot):
    def __init__(self):
        super().__init__("Figurehead", CardStats(coins=3))
        self.types.append(CardType.DURATION)

    def play_effect(self, game_state):
        game_state.current_player.duration.append(self)

    def on_duration(self, game_state):
        game_state.draw_cards(game_state.current_player, 2)


class Hammer(Loot):
    def __init__(self):
        super().__init__("Hammer", CardStats(coins=3))

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        affordable_cards = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                affordable_cards.append(card)

        if not affordable_cards:
            return

        gain = player.ai.choose_buy(game_state, affordable_cards + [None])
        if gain not in affordable_cards:
            gain = affordable_cards[0]

        game_state.supply[gain.name] -= 1
        game_state.gain_card(player, gain)


class Insignia(Loot):
    def __init__(self):
        super().__init__("Insignia", CardStats(coins=3))

    def play_effect(self, game_state):
        game_state.current_player.topdeck_gains = True


class Jewels(Loot):
    def __init__(self):
        super().__init__("Jewels", CardStats(coins=3, buys=1))
        self.types.append(CardType.DURATION)
        self.duration_persistent = True

    def play_effect(self, game_state):
        game_state.current_player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self in player.duration:
            player.duration.remove(self)
        player.deck.append(self)


class Orb(Loot):
    def __init__(self):
        super().__init__("Orb", CardStats())

    def play_effect(self, game_state):
        player = game_state.current_player
        actions = [c for c in player.discard if c.is_action]
        treasures = [c for c in player.discard if c.is_treasure]
        chosen = None
        if actions:
            chosen = player.ai.choose_action(game_state, actions + [None])
        if not chosen and treasures:
            chosen = player.ai.choose_treasure(game_state, treasures + [None])
        if chosen:
            player.discard.remove(chosen)
            player.in_play.append(chosen)
            chosen.on_play(game_state)
        else:
            player.coins += 3
            player.buys += 1


class PrizeGoat(Loot):
    def __init__(self):
        super().__init__("Prize Goat", CardStats(coins=3, buys=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        if player.hand:
            card = player.ai.choose_card_to_trash(
                game_state, list(player.hand) + [None]
            )
            if card:
                player.hand.remove(card)
                game_state.trash_card(player, card)


class PuzzleBox(Loot):
    def __init__(self):
        super().__init__("Puzzle Box", CardStats(coins=3, buys=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_action(game_state, player.hand + [None])
        if choice:
            player.hand.remove(choice)
            player.delayed_cards.append(choice)


class Sextant(Loot):
    def __init__(self):
        super().__init__("Sextant", CardStats(coins=3, buys=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        peek = []
        for _ in range(min(5, len(player.deck))):
            peek.append(player.deck.pop())
        to_keep = []
        for card in peek:
            if card.is_victory or card.name == "Curse":
                game_state.discard_card(player, card)
            else:
                to_keep.append(card)
        player.deck.extend(reversed(to_keep))


class Shield(Loot):
    def __init__(self):
        super().__init__("Shield", CardStats(coins=3, buys=1))
        self.types.append(CardType.REACTION)


class SpellScroll(Loot):
    def __init__(self):
        super().__init__("Spell Scroll", CardStats())
        self.types.append(CardType.ACTION)

    def play_effect(self, game_state):
        player = game_state.current_player
        # Trash this
        if self in player.in_play:
            player.in_play.remove(self)
        game_state.trash_card(player, self)

        from ..registry import get_card
        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins < 7
        ]
        if not affordable:
            return
        gain = player.ai.choose_buy(game_state, [get_card(n) for n in affordable])
        if gain is None:
            gain = get_card(affordable[0])
        game_state.supply[gain.name] -= 1
        game_state.gain_card(player, gain)
        if gain.is_action or gain.is_treasure:
            if gain in player.discard:
                player.discard.remove(gain)
            player.in_play.append(gain)
            gain.on_play(game_state)


class Staff(Loot):
    def __init__(self):
        super().__init__("Staff", CardStats(coins=3, buys=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        actions = [c for c in player.hand if c.is_action]
        if actions:
            card = player.ai.choose_action(game_state, actions + [None])
            if card:
                player.hand.remove(card)
                player.in_play.append(card)
                card.on_play(game_state)


class Sword(Loot):
    def __init__(self):
        super().__init__("Sword", CardStats(coins=3, buys=1))
        self.types.append(CardType.ATTACK)

    def play_effect(self, game_state):
        player = game_state.current_player

        def discard_to_four(target):
            if len(target.hand) <= 4:
                return

            discard_count = len(target.hand) - 4
            choices = list(target.hand)
            selected = target.ai.choose_cards_to_discard(
                game_state,
                target,
                choices,
                discard_count,
                reason="sword",
            )

            remaining_choices = list(choices)
            selected_cards = []

            for card in selected:
                if card in remaining_choices:
                    remaining_choices.remove(card)
                    selected_cards.append(card)

            while len(selected_cards) < discard_count and remaining_choices:
                selected_cards.append(remaining_choices.pop(0))

            for card in selected_cards:
                if card in target.hand:
                    target.hand.remove(card)
                    game_state.discard_card(target, card)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, discard_to_four)


LOOT_CARD_NAMES = [
    "Amphora",
    "Doubloons",
    "Endless Chalice",
    "Figurehead",
    "Hammer",
    "Insignia",
    "Jewels",
    "Orb",
    "Prize Goat",
    "Puzzle Box",
    "Sextant",
    "Shield",
    "Spell Scroll",
    "Staff",
    "Sword",
]

__all__ = [
    "Amphora",
    "Doubloons",
    "Endless Chalice",
    "Figurehead",
    "Hammer",
    "Insignia",
    "Jewels",
    "Orb",
    "Prize Goat",
    "Puzzle Box",
    "Sextant",
    "Shield",
    "Spell Scroll",
    "Staff",
    "Sword",
    "LOOT_CARD_NAMES",
]
