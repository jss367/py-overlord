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
        super().__init__("Amphora", CardStats(coins=3, buys=1))


class Doubloons(Loot):
    def __init__(self):
        super().__init__("Doubloons", CardStats(coins=3))

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if game_state.supply.get("Gold", 0) > 0:
            from ..registry import get_card

            game_state.supply["Gold"] -= 1
            gold = get_card("Gold")
            player.discard.append(gold)
            gold.on_gain(game_state, player)


class EndlessChalice(Loot):
    def __init__(self):
        super().__init__("Endless Chalice", CardStats(coins=1, buys=1))


class Figurehead(Loot):
    def __init__(self):
        super().__init__("Figurehead", CardStats(coins=3))


class Hammer(Loot):
    def __init__(self):
        super().__init__("Hammer", CardStats(coins=3))

    def play_effect(self, game_state):
        player = game_state.current_player
        from ..registry import get_card

        affordable = [
            name
            for name, count in game_state.supply.items()
            if count > 0 and get_card(name).cost.coins <= 4
        ]
        if affordable:
            gain = get_card(affordable[0])
            game_state.supply[gain.name] -= 1
            player.discard.append(gain)
            gain.on_gain(game_state, player)


class Insignia(Loot):
    def __init__(self):
        super().__init__("Insignia", CardStats(coins=3))


class Jewels(Loot):
    def __init__(self):
        super().__init__("Jewels", CardStats(coins=3, buys=1))


class Orb(Loot):
    def __init__(self):
        super().__init__("Orb", CardStats())


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


class Sextant(Loot):
    def __init__(self):
        super().__init__("Sextant", CardStats(coins=3, buys=1))


class Shield(Loot):
    def __init__(self):
        super().__init__("Shield", CardStats(coins=3, buys=1))
        self.types.append(CardType.REACTION)


class SpellScroll(Loot):
    def __init__(self):
        super().__init__("Spell Scroll", CardStats())


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
            while len(target.hand) > 4:
                discard = target.hand.pop(0)
                target.discard.append(discard)

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
