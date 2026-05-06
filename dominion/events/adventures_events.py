"""Implementation of the Adventures Events."""

from dominion.cards.base_card import CardCost
from dominion.cards.registry import get_card

from .base_event import Event


class Alms(Event):
    """$0 — once per turn, if no Treasures in play, gain a card up to $4."""

    def __init__(self):
        super().__init__("Alms", CardCost(coins=0))

    def may_be_bought(self, game_state, player) -> bool:
        if getattr(player, "alms_used_this_turn", False):
            return False
        if any(c.is_treasure for c in player.in_play):
            return False
        return True

    def on_buy(self, game_state, player) -> None:
        player.alms_used_this_turn = True
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if card.cost.coins <= 4 and card.cost.potions == 0 and card.cost.debt == 0:
                candidates.append(card)
        if not candidates:
            return
        choice = player.ai.choose_gain_for_alms(game_state, player, candidates)
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, get_card(choice.name))


class Borrow(Event):
    """$0 — once per turn: +1 Buy +$1; -1 Card token on your deck."""

    def __init__(self):
        super().__init__("Borrow", CardCost(coins=0))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "borrow_used_this_turn", False)

    def on_buy(self, game_state, player) -> None:
        player.borrow_used_this_turn = True
        player.buys += 1
        player.coins += 1
        player.minus_card_tokens += 1


class Quest(Event):
    """$0 — discard an Attack, two Curses, or six cards. Gain a Gold."""

    def __init__(self):
        super().__init__("Quest", CardCost(coins=0))

    def on_buy(self, game_state, player) -> None:
        # Choose which way to pay.
        attack = next((c for c in player.hand if c.is_attack), None)
        curses = [c for c in player.hand if c.name == "Curse"]
        options = []
        if attack is not None:
            options.append("attack")
        if len(curses) >= 2:
            options.append("two_curses")
        if len(player.hand) >= 6:
            options.append("six_cards")
        if not options:
            return
        chosen = player.ai.choose_quest_mode(game_state, player, options)
        if chosen == "attack":
            player.hand.remove(attack)
            game_state.discard_card(player, attack)
        elif chosen == "two_curses":
            for c in curses[:2]:
                player.hand.remove(c)
                game_state.discard_card(player, c)
        elif chosen == "six_cards":
            picks = player.ai.choose_cards_to_discard(
                game_state, player, list(player.hand), 6, reason="quest"
            )
            for card in picks[:6]:
                if card in player.hand:
                    player.hand.remove(card)
                    game_state.discard_card(player, card)
        else:
            return
        if game_state.supply.get("Gold", 0) > 0:
            game_state.supply["Gold"] -= 1
            game_state.gain_card(player, get_card("Gold"))


class Save(Event):
    """$1 — +1 Buy. Set aside a card from your hand. Returns next turn."""

    def __init__(self):
        super().__init__("Save", CardCost(coins=1))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        if not player.hand:
            return
        card = player.ai.choose_card_to_save(game_state, player, list(player.hand))
        if card is None or card not in player.hand:
            return
        player.hand.remove(card)
        player.save_set_aside.append(card)


class ScoutingParty(Event):
    """$2 — +1 Buy. Look at top 5 of your deck. Discard 3, put back 2."""

    def __init__(self):
        super().__init__("Scouting Party", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.buys += 1
        revealed = []
        while len(revealed) < 5:
            if not player.deck and player.discard:
                player.shuffle_discard_into_deck()
            if not player.deck:
                break
            revealed.append(player.deck.pop())
        if not revealed:
            return
        # Discard 3 chosen by AI; remainder goes back on top.
        picks = player.ai.choose_cards_to_discard(
            game_state, player, list(revealed), 3, reason="scouting_party"
        )
        for card in picks[:3]:
            if card in revealed:
                revealed.remove(card)
                game_state.discard_card(player, card)
        # Force 3 discards if AI undershot.
        while len(revealed) > 2 and revealed:
            fallback = min(revealed, key=lambda c: (c.cost.coins, c.name))
            revealed.remove(fallback)
            game_state.discard_card(player, fallback)
        # Remaining 2 go back on top in chosen order.
        ordered = player.ai.order_cards_for_topdeck(game_state, player, revealed)
        for card in ordered:
            player.deck.append(card)


class TravellingFair(Event):
    """$2 — +2 Buys. While this turn, gains may be topdecked."""

    def __init__(self):
        super().__init__("Travelling Fair", CardCost(coins=2))

    def on_buy(self, game_state, player) -> None:
        player.buys += 2
        player.travelling_fair_active = True


class Bonfire(Event):
    """$3 — Trash up to 2 cards from in play."""

    def __init__(self):
        super().__init__("Bonfire", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        if not player.in_play:
            return
        picks = player.ai.choose_cards_to_trash(
            game_state, list(player.in_play), 2
        )
        for card in picks[:2]:
            if card in player.in_play:
                player.in_play.remove(card)
                game_state.trash_card(player, card)


class Expedition(Event):
    """$3 — Draw 2 extra cards at end of turn."""

    def __init__(self):
        super().__init__("Expedition", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        player.expedition_extra_draws += 2


class Ferry(Event):
    """$3 — Place your -$2 cost token on an Action Supply pile."""

    def __init__(self):
        super().__init__("Ferry", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        pile = player.ai.choose_pile_for_token(game_state, player, "-$2 cost")
        if pile is None:
            return
        game_state.move_player_token(player, "-$2 cost", pile)


class Plan(Event):
    """$3 — Place your trashing token on an Action Supply pile."""

    def __init__(self):
        super().__init__("Plan", CardCost(coins=3))

    def on_buy(self, game_state, player) -> None:
        pile = player.ai.choose_pile_for_token(game_state, player, "trash")
        if pile is None:
            return
        game_state.move_player_token(player, "trash", pile)
        # Keep a per-player set of pile names with the trash token for fast
        # lookup during buy phase.
        prior = game_state.player_token_pile(player, "trash")
        # Recompute: player's plan_trash_piles = {prior pile} (only one token).
        if prior is not None:
            player.plan_trash_piles = {prior}


class Mission(Event):
    """$4 — Take an extra turn after this one (no buys)."""

    def __init__(self):
        super().__init__("Mission", CardCost(coins=4))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "mission_used_this_turn", False)

    def on_buy(self, game_state, player) -> None:
        player.mission_used_this_turn = True
        # Schedule an extra turn for this player. The "no buys" restriction
        # applies to the GRANTED extra turn, not the current turn — setting it
        # here would immediately shut off any remaining buys on the current
        # turn. Instead, we defer the restriction to the start of the extra
        # turn (see GameState start-of-turn handling, which detects the
        # Mission-granted turn and sets ``mission_no_buy_turn`` then).
        player.mission_extra_turn_pending = True
        game_state.extra_turn = True


class Pilgrimage(Event):
    """$4 — Once per turn, flip Journey token. If face up, gain copies of up
    to 3 differently-named Action cards in play."""

    def __init__(self):
        super().__init__("Pilgrimage", CardCost(coins=4))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "pilgrimage_used_this_turn", False)

    def on_buy(self, game_state, player) -> None:
        player.pilgrimage_used_this_turn = True
        player.journey_token_face_up = not player.journey_token_face_up
        if not player.journey_token_face_up:
            return
        # Choose up to 3 differently-named Action cards in play.
        names_in_play = []
        seen = set()
        for c in player.in_play:
            if c.is_action and c.name not in seen:
                seen.add(c.name)
                names_in_play.append(c.name)
        if not names_in_play:
            return
        # Sort by cost desc, take up to 3.
        ordered = sorted(
            names_in_play,
            key=lambda n: (get_card(n).cost.coins, n),
            reverse=True,
        )
        for name in ordered[:3]:
            if game_state.supply.get(name, 0) <= 0:
                continue
            game_state.supply[name] -= 1
            game_state.gain_card(player, get_card(name))


class Ball(Event):
    """$5 — Take your -$1 token. Gain 2 cards each costing up to $4."""

    def __init__(self):
        super().__init__("Ball", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        # -$1 token: deduct $1 next turn (we apply immediately for simplicity)
        player.coins = max(0, player.coins - 1)
        # Gain 2 cards costing up to $4 each.
        for _ in range(2):
            candidates = []
            for name, count in game_state.supply.items():
                if count <= 0:
                    continue
                try:
                    card = get_card(name)
                except ValueError:
                    continue
                if card.cost.coins <= 4 and card.cost.potions == 0 and card.cost.debt == 0:
                    candidates.append(card)
            if not candidates:
                break
            choice = player.ai.choose_gain_for_ball(game_state, player, candidates)
            if choice is None:
                break
            if game_state.supply.get(choice.name, 0) <= 0:
                continue
            game_state.supply[choice.name] -= 1
            game_state.gain_card(player, get_card(choice.name))


class Raid(Event):
    """$5 — Each other player with 5+ in hand discards an Attack. Gain a
    Silver per Silver in play."""

    def __init__(self):
        super().__init__("Raid", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        # Per the printed rules: each other player discards an Attack from
        # their hand if hand is 5+. Here we use a more permissive
        # interpretation matching the published Adventures Raid: each other
        # player puts a -1 Card token on their deck.
        for other in game_state.players:
            if other is player:
                continue
            other.minus_card_tokens += 1
        silvers = sum(1 for c in player.in_play if c.name == "Silver")
        for _ in range(silvers):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))


class Seaway(Event):
    """$5 — Gain an Action up to $4. Place your +1 Buy token on its pile."""

    def __init__(self):
        super().__init__("Seaway", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        candidates = []
        for name, count in game_state.supply.items():
            if count <= 0:
                continue
            try:
                card = get_card(name)
            except ValueError:
                continue
            if (
                card.is_action
                and card.cost.coins <= 4
                and card.cost.potions == 0
                and card.cost.debt == 0
            ):
                candidates.append(card)
        if not candidates:
            return
        choice = player.ai.choose_gain_for_seaway(game_state, player, candidates)
        if choice is None or game_state.supply.get(choice.name, 0) <= 0:
            return
        game_state.supply[choice.name] -= 1
        game_state.gain_card(player, get_card(choice.name))
        game_state.move_player_token(player, "+1 Buy", choice.name)


class Trade(Event):
    """$5 — Trash up to 2 cards from your hand. Gain a Silver for each."""

    def __init__(self):
        super().__init__("Trade", CardCost(coins=5))

    def on_buy(self, game_state, player) -> None:
        if not player.hand:
            return
        picks = player.ai.choose_cards_to_trash(
            game_state, list(player.hand), 2
        )
        trashed = 0
        for card in picks[:2]:
            if card in player.hand:
                player.hand.remove(card)
                game_state.trash_card(player, card)
                trashed += 1
        for _ in range(trashed):
            if game_state.supply.get("Silver", 0) <= 0:
                break
            game_state.supply["Silver"] -= 1
            game_state.gain_card(player, get_card("Silver"))


class LostArts(Event):
    """$6 — Place your +1 Action token on an Action Supply pile."""

    def __init__(self):
        super().__init__("Lost Arts", CardCost(coins=6))

    def on_buy(self, game_state, player) -> None:
        pile = player.ai.choose_pile_for_token(game_state, player, "+1 Action")
        if pile is None:
            return
        game_state.move_player_token(player, "+1 Action", pile)


class Inheritance(Event):
    """$7 — Once per game, set aside a non-Victory Action ($0-$4) from the
    Supply. Each starting Estate is treated as that card during your turn."""

    def __init__(self):
        super().__init__("Inheritance", CardCost(coins=7))

    def may_be_bought(self, game_state, player) -> bool:
        return not getattr(player, "inheritance_used", False)

    def on_buy(self, game_state, player) -> None:
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
            if card.is_victory:
                continue
            if card.cost.coins > 4 or card.cost.potions != 0 or card.cost.debt != 0:
                continue
            candidates.append(card)
        if not candidates:
            return
        choice = player.ai.choose_card_to_inherit(game_state, player, candidates)
        if choice is None:
            return
        # Remove a copy from supply to "set aside".
        if game_state.supply.get(choice.name, 0) > 0:
            game_state.supply[choice.name] -= 1
        player.inherited_action_name = choice.name
        player.inheritance_used = True


class Pathfinding(Event):
    """$8 — Place your +1 Card token on an Action Supply pile."""

    def __init__(self):
        super().__init__("Pathfinding", CardCost(coins=8))

    def on_buy(self, game_state, player) -> None:
        pile = player.ai.choose_pile_for_token(game_state, player, "+1 Card")
        if pile is None:
            return
        game_state.move_player_token(player, "+1 Card", pile)
