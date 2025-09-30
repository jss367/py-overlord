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

        affordable: list[Card] = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            card = get_card(name)
            if card.cost.coins <= 4:
                affordable.append(card)

        if not affordable:
            return

        affordable.sort(key=lambda c: (c.cost.coins, c.name))
        gain = player.ai.choose_buy(game_state, affordable)
        if gain not in affordable:
            gain = affordable[0]

        game_state.supply[gain.name] -= 1
        game_state.gain_card(player, gain)


class Insignia(Loot):
    def __init__(self):
        super().__init__("Insignia", CardStats(coins=3))

    def play_effect(self, game_state):
        player = game_state.current_player
        player.optional_topdeck_gains = True


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
        player.deck = [self] + player.deck
        self.duration_persistent = False


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
            card = player.ai.choose_card_to_trash(game_state, player.hand)
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
        choice = player.ai.choose_card_to_set_aside(
            game_state, player, list(player.hand), reason="puzzle_box"
        )
        if choice and choice in player.hand:
            player.hand.remove(choice)
            player.end_of_turn_set_aside.append(choice)


class Sextant(Loot):
    def __init__(self):
        super().__init__("Sextant", CardStats(coins=3, buys=1))

    def play_effect(self, game_state):
        player = game_state.current_player
        peek: list[Card] = []
        for _ in range(5):
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            peek.append(player.deck.pop())

        if not peek:
            return

        chosen_to_discard = player.ai.choose_cards_to_discard(
            game_state, player, peek.copy(), len(peek), reason="sextant"
        )
        discarded: list[Card] = []
        if chosen_to_discard:
            for card in chosen_to_discard:
                if card in peek and card not in discarded:
                    discarded.append(card)

        for card in discarded:
            peek.remove(card)
            game_state.discard_card(player, card)

        if not peek:
            return

        ordered = player.ai.order_cards_for_sextant(game_state, player, peek.copy())
        if (
            not ordered
            or len(ordered) != len(peek)
            or {id(card) for card in ordered} != {id(card) for card in peek}
        ):
            ordered = peek

        for card in reversed(ordered):
            player.deck.append(card)


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
            excess = len(target.hand) - 4
            if excess <= 0:
                return

            chosen = target.ai.choose_cards_to_discard(
                game_state, target, list(target.hand), excess, reason="sword"
            )
            discards: list[Card] = []
            if chosen:
                for card in chosen:
                    if card in target.hand and card not in discards:
                        discards.append(card)

            while len(discards) < excess:
                for card in target.hand:
                    if card not in discards:
                        discards.append(card)
                        if len(discards) == excess:
                            break

            for card in discards:
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
