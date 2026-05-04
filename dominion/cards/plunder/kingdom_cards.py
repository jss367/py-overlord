"""All remaining Plunder kingdom cards.

Each class implements one Plunder card. Loots / pre-existing cards
(Astrolabe, Barbarian, Crew, First Mate, Flagship, Harbor Village,
Highwayman, Pickaxe, Trickster) live elsewhere in this package.
"""

import random

from ..base_card import Card, CardCost, CardStats, CardType


def _gain_random_loot(game_state, player):
    """Gain a random face-up Loot for this player. Returns the gained card."""
    from ..registry import get_card
    from .loot_cards import LOOT_CARD_NAMES

    loot_name = random.choice(LOOT_CARD_NAMES)
    loot = get_card(loot_name)
    return game_state.gain_card(player, loot)


# ---------------------------------------------------------------------------
# $2 cards
# ---------------------------------------------------------------------------


class Cage(Card):
    """$2 Treasure-Duration. Set aside up to 4 gained cards; return at end of turn."""

    def __init__(self):
        super().__init__(
            name="Cage",
            cost=CardCost(coins=2),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        gained_names = list(getattr(player, "gained_cards_this_turn", []))
        gained_in_discard = [c for c in player.discard if c.name in gained_names]
        gained_in_discard.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        for card in gained_in_discard[:4]:
            if card in player.discard:
                player.discard.remove(card)
                self.set_aside.append(card)

    def on_duration(self, game_state):
        player = game_state.current_player
        if self.set_aside:
            player.hand.extend(self.set_aside)
            self.set_aside = []
        self.duration_persistent = False


class Grotto(Card):
    """$2 Action-Duration: +1 Action. Set aside up to 4; discard, draw that many."""

    def __init__(self):
        super().__init__(
            name="Grotto",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True
        self.set_aside: list = []

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        if not player.hand:
            return
        candidates = sorted(
            player.hand,
            key=lambda c: (c.cost.coins, c.is_victory or c.name == "Curse"),
        )
        choice_count = min(4, len(player.hand))
        for card in candidates[:choice_count]:
            player.hand.remove(card)
            self.set_aside.append(card)

    def on_duration(self, game_state):
        player = game_state.current_player
        n = len(self.set_aside)
        for c in self.set_aside:
            player.discard.append(c)
        self.set_aside = []
        if n:
            game_state.draw_cards(player, n)
        self.duration_persistent = False


class JewelledEgg(Card):
    """$2 Treasure: $1. On gain or play: gain a Loot. On trash: +1 Buy +$4."""

    def __init__(self):
        super().__init__(
            name="Jewelled Egg",
            cost=CardCost(coins=2),
            stats=CardStats(coins=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        _gain_random_loot(game_state, player)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        _gain_random_loot(game_state, player)

    def on_trash(self, game_state, player):
        super().on_trash(game_state, player)
        player.buys += 1
        player.coins += 4


class Search(Card):
    """$2 Action-Duration: +$2. Start of next turn, gain a Loot if no cards on Search."""

    def __init__(self):
        super().__init__(
            name="Search",
            cost=CardCost(coins=2),
            stats=CardStats(coins=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        _gain_random_loot(game_state, player)
        self.duration_persistent = False


class Shaman(Card):
    """$2 Action: +1 Action +$1. May trash. Start of turn, gain from trash up to $6."""

    def __init__(self):
        super().__init__(
            name="Shaman",
            cost=CardCost(coins=2),
            stats=CardStats(actions=1, coins=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)

    def on_duration(self, game_state):
        player = game_state.current_player
        candidates = [
            c for c in game_state.trash
            if c.cost.coins <= 6 and c.cost.potions == 0 and c.cost.debt == 0
        ]
        if candidates:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            pick = candidates[0]
            game_state.trash.remove(pick)
            game_state.gain_card(player, pick, from_supply=False)
        self.duration_persistent = False


# ---------------------------------------------------------------------------
# $3 cards
# ---------------------------------------------------------------------------


class SecludedShrine(Card):
    """$3 Action-Duration: +1 Buy +$1. Next turn, may trash up to 2 cards."""

    def __init__(self):
        super().__init__(
            name="Secluded Shrine",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        for _ in range(2):
            if not player.hand:
                break
            choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
            if not choice or choice not in player.hand:
                break
            player.hand.remove(choice)
            game_state.trash_card(player, choice)
        self.duration_persistent = False


class Siren(Card):
    """$3 Action-Attack: Each other gains a Curse. On gain: gain an Action card."""

    def __init__(self):
        super().__init__(
            name="Siren",
            cost=CardCost(coins=3),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                game_state.give_curse_to_player(target)

            game_state.attack_player(other, attack)

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        from ..registry import get_card

        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_action and not card.is_victory:
                candidates.append(card)
        if not candidates:
            return
        candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        pick = candidates[0]
        if game_state.supply.get(pick.name, 0) > 0:
            game_state.supply[pick.name] -= 1
            game_state.gain_card(player, pick)


class Stowaway(Card):
    """$3 Treasure-Duration-Reaction: $1 +1 Card now and next turn.
    React to opponent gaining Victory by setting aside; play next turn."""

    def __init__(self):
        super().__init__(
            name="Stowaway",
            cost=CardCost(coins=3),
            stats=CardStats(coins=1, cards=1),
            types=[CardType.TREASURE, CardType.DURATION, CardType.REACTION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 1)
        self.duration_persistent = False

    def on_opponent_gain(self, game_state, owner, gainer, gained_card):
        if not gained_card.is_victory:
            return
        if self not in owner.hand:
            return
        owner.hand.remove(self)
        owner.duration.append(self)
        self.duration_persistent = True


# ---------------------------------------------------------------------------
# $4 cards
# ---------------------------------------------------------------------------


class Abundance(Card):
    """$4 Action-Duration: Start of next turn, gain a Loot."""

    def __init__(self):
        super().__init__(
            name="Abundance",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        _gain_random_loot(game_state, player)
        self.duration_persistent = False


class CabinBoy(Card):
    """$4 Action-Duration: +1 Card +1 Action. Start of next turn,
    choose: +$2 OR trash this and gain a Duration card."""

    def __init__(self):
        super().__init__(
            name="Cabin Boy",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        duration_options = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.is_duration and card.cost.coins >= 5:
                duration_options.append(card)

        if duration_options:
            duration_options.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            pick = duration_options[0]
            if self in player.duration:
                player.duration.remove(self)
            if self in player.in_play:
                player.in_play.remove(self)
            game_state.trash.append(self)
            self.on_trash(game_state, player)
            game_state.supply[pick.name] -= 1
            game_state.gain_card(player, pick)
            self.duration_persistent = False
        else:
            player.coins += 2
            self.duration_persistent = False


class Crucible(Card):
    """$4 Treasure: +$1 per card trashed this turn. On play: trash a card."""

    def __init__(self):
        super().__init__(
            name="Crucible",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if player.hand:
            choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
            if choice and choice in player.hand:
                player.hand.remove(choice)
                game_state.trash_card(player, choice)
        player.coins += getattr(player, "cards_trashed_this_turn", 0)


class FortuneHunter(Card):
    """$4 Action: +$2. Look at top 3; play a Treasure from among; rest back."""

    def __init__(self):
        super().__init__(
            name="Fortune Hunter",
            cost=CardCost(coins=4),
            stats=CardStats(coins=2),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if len(player.deck) < 3 and player.discard:
            player.shuffle_discard_into_deck()
        top: list = []
        while len(top) < 3 and player.deck:
            top.append(player.deck.pop())
        treasures_top = [c for c in top if c.is_treasure]
        if treasures_top:
            treasures_top.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            played = treasures_top[0]
            top.remove(played)
            player.in_play.append(played)
            played.on_play(game_state)
        for c in top:
            player.deck.append(c)


class Gondola(Card):
    """$4 Treasure-Duration: $0 now and +$2 next turn. On gain: may play an Action."""

    def __init__(self):
        super().__init__(
            name="Gondola",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 2
        self.duration_persistent = False

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        choice = player.ai.choose_action(game_state, actions_in_hand + [None])
        if choice is None:
            return
        player.hand.remove(choice)
        player.in_play.append(choice)
        choice.on_play(game_state)


class LandingParty(Card):
    """$4 Action-Duration: +1 Buy +1 Card. Next gained Treasure: top-deck both."""

    def __init__(self):
        super().__init__(
            name="Landing Party",
            cost=CardCost(coins=4),
            stats=CardStats(cards=1, buys=1),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        game_state.landing_party_pending.setdefault(id(player), []).append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        pending = game_state.landing_party_pending.get(id(player), [])
        if self not in pending:
            self.duration_persistent = False


class Mapmaker(Card):
    """$4 Action: Look at top 4. Put 2 into hand; discard rest."""

    def __init__(self):
        super().__init__(
            name="Mapmaker",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        looked: list = []
        while len(looked) < 4:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            looked.append(player.deck.pop())
        looked_sorted = sorted(
            looked,
            key=lambda c: (not c.is_victory and c.name != "Curse", c.cost.coins, c.name),
            reverse=True,
        )
        for card in looked_sorted[:2]:
            player.hand.append(card)
        for card in looked_sorted[2:]:
            player.discard.append(card)


class Maroon(Card):
    """$4 Action: Trash a card from your hand. +1 Card per type that card has."""

    def __init__(self):
        super().__init__(
            name="Maroon",
            cost=CardCost(coins=4),
            stats=CardStats(),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, list(player.hand))
        if not choice or choice not in player.hand:
            choice = player.hand[0]
        types_count = len(choice.types)
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        if types_count:
            game_state.draw_cards(player, types_count)


class Rope(Card):
    """$4 Treasure-Duration: +1 Buy. +$1 now and next turn. On gain: may trash."""

    def __init__(self):
        super().__init__(
            name="Rope",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 1
        self.duration_persistent = False

    def on_gain(self, game_state, player):
        super().on_gain(game_state, player)
        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if choice and choice in player.hand:
            player.hand.remove(choice)
            game_state.trash_card(player, choice)


class SwampShacks(Card):
    """$4 Action-Attack: +1 Card +1 Action +$1. Each other 5+ → discards one."""

    def __init__(self):
        super().__init__(
            name="Swamp Shacks",
            cost=CardCost(coins=4),
            stats=CardStats(actions=1, cards=1, coins=1),
            types=[CardType.ACTION, CardType.ATTACK],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                if len(target.hand) >= 5:
                    candidate = min(target.hand, key=lambda c: (c.cost.coins, c.name))
                    target.hand.remove(candidate)
                    game_state.discard_card(target, candidate)

            game_state.attack_player(other, attack)


class Tools(Card):
    """$4 Treasure: +$1 +1 Buy. Take any card you've gained this turn (to hand)."""

    def __init__(self):
        super().__init__(
            name="Tools",
            cost=CardCost(coins=4),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        gained_names = list(getattr(player, "gained_cards_this_turn", []))
        if not gained_names:
            return
        candidates = [c for c in player.discard if c.name in gained_names]
        if not candidates:
            return
        candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        pick = candidates[0]
        player.discard.remove(pick)
        player.hand.append(pick)


# ---------------------------------------------------------------------------
# $5 cards
# ---------------------------------------------------------------------------


class BuriedTreasure(Card):
    """$5 Treasure-Duration: +1 Buy. Start of next turn, +$3."""

    def __init__(self):
        super().__init__(
            name="Buried Treasure",
            cost=CardCost(coins=5),
            stats=CardStats(buys=1),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        player.coins += 3
        self.duration_persistent = False


class Cutthroat(Card):
    """$5 Action-Attack-Duration: +1 Card. 5+ → discard down to 3.
    Start of next turn, gain a Loot."""

    def __init__(self):
        super().__init__(
            name="Cutthroat",
            cost=CardCost(coins=5),
            stats=CardStats(cards=1),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                while len(target.hand) > 3:
                    cand = min(target.hand, key=lambda c: (c.cost.coins, c.name))
                    target.hand.remove(cand)
                    game_state.discard_card(target, cand)

            game_state.attack_player(other, attack)

    def on_duration(self, game_state):
        player = game_state.current_player
        _gain_random_loot(game_state, player)
        self.duration_persistent = False


class Enlarge(Card):
    """$5 Treasure-Duration: Now and start of next turn, trash a card and gain
    one costing up to $2 more."""

    def __init__(self):
        super().__init__(
            name="Enlarge",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)
        self._trash_and_gain(game_state, player)

    def on_duration(self, game_state):
        player = game_state.current_player
        self._trash_and_gain(game_state, player)
        self.duration_persistent = False

    def _trash_and_gain(self, game_state, player):
        from ..registry import get_card

        if not player.hand:
            return
        choice = player.ai.choose_card_to_trash(game_state, player.hand + [None])
        if not choice or choice not in player.hand:
            return
        max_cost = choice.cost.coins + 2
        player.hand.remove(choice)
        game_state.trash_card(player, choice)
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= max_cost and card.cost.potions == 0 and card.cost.debt == 0:
                candidates.append(card)
        if candidates:
            candidates.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
            pick = candidates[0]
            game_state.supply[pick.name] -= 1
            game_state.gain_card(player, pick)


class Figurine(Card):
    """$5 Treasure: $1 +1 Buy. On discard from play: may discard Action for +1 Card +1 Action."""

    def __init__(self):
        super().__init__(
            name="Figurine",
            cost=CardCost(coins=5),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        pass

    def react_to_discard(self, game_state, player):
        actions_in_hand = [c for c in player.hand if c.is_action]
        if not actions_in_hand:
            return
        choice = min(actions_in_hand, key=lambda c: (c.cost.coins, c.name))
        player.hand.remove(choice)
        game_state.discard_card(player, choice)
        game_state.draw_cards(player, 1)
        player.actions += 1


class Frigate(Card):
    """$5 Action-Attack-Duration: +$3. Start of next turn, 5+ → discard down to 4."""

    def __init__(self):
        super().__init__(
            name="Frigate",
            cost=CardCost(coins=5),
            stats=CardStats(coins=3),
            types=[CardType.ACTION, CardType.DURATION, CardType.ATTACK],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        for other in game_state.players:
            if other is player:
                continue

            def attack(target):
                while len(target.hand) > 4:
                    cand = min(target.hand, key=lambda c: (c.cost.coins, c.name))
                    target.hand.remove(cand)
                    game_state.discard_card(target, cand)

            game_state.attack_player(other, attack)
        self.duration_persistent = False


class Longship(Card):
    """$5 Action-Duration: +2 Actions. Start of next turn, +2 Cards."""

    def __init__(self):
        super().__init__(
            name="Longship",
            cost=CardCost(coins=5),
            stats=CardStats(actions=2),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        player = game_state.current_player
        game_state.draw_cards(player, 2)
        self.duration_persistent = False


class MiningRoad(Card):
    """$5 Action: +1 Action +1 Buy +$1. First Treasure gained on your turn,
    gain a Treasure to hand."""

    def __init__(self):
        super().__init__(
            name="Mining Road",
            cost=CardCost(coins=5),
            stats=CardStats(actions=1, buys=1, coins=1),
            types=[CardType.ACTION],
        )

    def play_effect(self, game_state):
        pass


class Pendant(Card):
    """$5 Treasure: At start of cleanup, +$1 per differently-named Treasure in play."""

    def __init__(self):
        super().__init__(
            name="Pendant",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        pass


class Quartermaster(Card):
    """$5 Action-Duration: At start of each turn, choose: gain to mat, or take all."""

    def __init__(self):
        super().__init__(
            name="Quartermaster",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        self.duration_persistent = True


class SilverMine(Card):
    """$5 Action-Duration: Start of next turn, gain a Silver to your hand."""

    def __init__(self):
        super().__init__(
            name="Silver Mine",
            cost=CardCost(coins=5),
            stats=CardStats(),
            types=[CardType.ACTION, CardType.DURATION],
        )
        self.duration_persistent = True

    def play_effect(self, game_state):
        player = game_state.current_player
        if self not in player.duration:
            player.duration.append(self)

    def on_duration(self, game_state):
        from ..registry import get_card

        player = game_state.current_player
        if game_state.supply.get("Silver", 0) > 0:
            game_state.supply["Silver"] -= 1
            silver = get_card("Silver")
            gained = game_state.gain_card(player, silver)
            if gained in player.discard:
                player.discard.remove(gained)
                player.hand.append(gained)
        self.duration_persistent = False


# ---------------------------------------------------------------------------
# $6+ cards
# ---------------------------------------------------------------------------


class SackOfLoot(Card):
    """$6 Treasure: $1 +1 Buy. Gain a Loot."""

    def __init__(self):
        super().__init__(
            name="Sack of Loot",
            cost=CardCost(coins=6),
            stats=CardStats(coins=1, buys=1),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        _gain_random_loot(game_state, player)


class KingsCache(Card):
    """$7 Treasure: $3. On play: may play a Treasure 3 times."""

    def __init__(self):
        super().__init__(
            name="King's Cache",
            cost=CardCost(coins=7),
            stats=CardStats(coins=3),
            types=[CardType.TREASURE],
        )

    def play_effect(self, game_state):
        player = game_state.current_player
        treasures_in_hand = [c for c in player.hand if c.is_treasure]
        if not treasures_in_hand:
            return
        treasures_in_hand.sort(key=lambda c: (c.cost.coins, c.name), reverse=True)
        choice = treasures_in_hand[0]
        player.hand.remove(choice)
        player.in_play.append(choice)
        for _ in range(3):
            choice.on_play(game_state)
