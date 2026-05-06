"""Page (Adventures) and the Page traveller chain.

Page → Treasure Hunter → Warrior → Hero → Champion.

Page is in the Supply; the rest are non-Supply piles spawned alongside Page.
"""

from ..base_card import Card, CardCost, CardStats, CardType


class Page(Card):
    next_traveller = "Treasure Hunter"

    def __init__(self):
        super().__init__(
            name="Page",
            cost=CardCost(coins=2),
            stats=CardStats(cards=1, actions=1),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def get_additional_piles(self):
        # Page brings the rest of the chain into existence, 5 of each.
        return {
            "Treasure Hunter": 5,
            "Warrior": 5,
            "Hero": 5,
            "Champion": 5,
        }


class TreasureHunter(Card):
    next_traveller = "Warrior"

    def __init__(self):
        super().__init__(
            name="Treasure Hunter",
            cost=CardCost(coins=3),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        # Non-supply: can't be bought, only acquired by exchange.
        return False

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        idx = game_state.players.index(player)
        right_idx = (idx + 1) % len(game_state.players)
        right = game_state.players[right_idx]
        gained_last = len(getattr(right, "gained_cards_last_turn", []))
        for _ in range(gained_last):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))


class Warrior(Card):
    next_traveller = "Hero"

    def __init__(self):
        super().__init__(
            name="Warrior",
            cost=CardCost(coins=4),
            stats=CardStats(cards=2),
            types=[CardType.ACTION, CardType.ATTACK, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        # Count Travellers in play (including this one). Warrior is in
        # ``in_play`` while play_effect runs.
        traveller_count = sum(1 for c in player.in_play if c.is_traveller)
        if traveller_count <= 0:
            traveller_count = 1

        def attack_target(target):
            for _ in range(traveller_count):
                if not target.deck and target.discard:
                    target.shuffle_discard_into_deck()
                if not target.deck:
                    break
                top = target.deck.pop()
                if 3 <= top.cost.coins <= 4:
                    game_state.trash_card(target, top)
                else:
                    game_state.discard_card(target, top)

        for other in game_state.players:
            if other is player:
                continue
            game_state.attack_player(other, attack_target, attacker=player, attack_card=self)


class Hero(Card):
    next_traveller = "Champion"

    def __init__(self):
        super().__init__(
            name="Hero",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.TRAVELLER],
        )

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        treasures = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_treasure:
                treasures.append(card)
        if not treasures:
            return
        choice = player.ai.choose_treasure_for_hero(game_state, player, treasures)
        if choice is None:
            return
        if game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, get_card(choice.name))


class Champion(Card):
    """Action-Duration. +1 Action. While in play: opponents' Attacks don't
    affect you, and your Action plays give +1 Action. Stays in play.
    """

    next_traveller = None

    def __init__(self):
        super().__init__(
            name="Champion",
            cost=CardCost(coins=6),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION, CardType.TRAVELLER],
        )
        self.duration_persistent = True

    def starting_supply(self, game_state) -> int:
        return 5

    def may_be_bought(self, game_state) -> bool:
        return False

    def play_effect(self, game_state):
        player = game_state.current_player
        player.actions += 1
        player.champions_in_play += 1
        if self in player.in_play:
            player.in_play.remove(self)
        player.duration.append(self)

    def on_duration(self, game_state):
        # Stays in play forever; nothing special at start of turn besides
        # Champion bookkeeping (already counted).
        self.duration_persistent = True

    def react_to_attack(self, game_state, player, attacker, attack_card) -> bool:
        # Champions in play protect their owner from attacks.
        if any(c.name == "Champion" for c in player.duration):
            return True
        return False
