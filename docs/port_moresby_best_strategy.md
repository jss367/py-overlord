# Port Moresby Board Strategy Search

Board: `boards/port_moresby.txt`

Kingdom:

- Daimyo (6 Debt)
- Secluded Shrine
- Carpenter
- Messenger
- Swamp Shacks
- Trail
- Barbarian
- Falconer
- Quartermaster
- Sculptor
- Event: Seaway
- Landmark: Fountain

## Simulator fixes made before searching

The pre-search audit compared all twelve implementations with the printed
card text (verified against the Dominion Strategy wiki card data). Six
rules defects were found and fixed first, with tests. Two of them changed
the board's whole character:

1. **Swamp Shacks was a different card.** The simulator had it as a
   cantrip attack (+1 Card +1 Action +$1, each other player discards).
   The real card is the board's only village and only draw:
   "+2 Actions, +1 Card per 3 cards you have in play (round down)".
2. **Falconer's reaction was invented.** The simulator revealed it to gain
   a card cheaper than whatever an opponent gained. The real reaction is
   "when any player gains a card with 2 or more types, you may play this
   from your hand" — it fires on your own gains too, and a played Falconer
   gains a card costing less than $5 to hand. Trail is Action-Reaction, so
   Falconer → Trail → Falconer chains are now possible.
3. **Secluded Shrine** trashed at the start of the next turn and had a
   phantom +1 Buy. The real card is +$1 and "the next time you gain a
   Treasure, trash up to 2 cards from your hand" (any turn, fires once).
4. **Quartermaster** took every set-aside card at once. The real choice is
   "put *a* card from this into your hand". Each Quartermaster keeps its
   own set-aside pile (a second copy cannot take the Silver the first one
   just gained), the pile survives the endgame guard's cloned game state,
   and set-aside cards count as owned at game end (they count for
   Fountain's Copper total).
5. **Carpenter** gained up to $5 flat after trashing and gave no +1 Card
   on the no-empty-piles branch. The real card is "+1 Action and gain up
   to $4" / "trash a card, gain a card costing up to $2 more than it".
6. **A trashed Trail returned to the trash** after reacting; per the
   official FAQ it stays in play (you get it back).

Two smaller corrections: every $4 gainer on the board (Falconer, Sculptor,
Carpenter, Messenger) could gain Daimyo because its coin cost is 0 — Debt
costs are now excluded, as they are in the real cost comparison — and a
Barbarian victim now chooses which cheaper card to gain instead of always
taking the priciest.

Two new AI hooks were added for the board's decisions:
`should_play_falconer` and `choose_quartermaster_option`
(`("gain", card)` or `("take", card)`), both overridable on a strategy.

## Board texture

- **Fountain** pays 15 VP (2.5 Provinces) for holding 10+ Coppers. Every
  deck starts with 7. Sculptor gains a Copper to hand for +1 Villager, so
  the bonus is nearly free for a Sculptor deck; other decks pay a Buy
  per Copper. Nothing here should ever trash a Copper.
- **Trail plays itself when gained**, so each $4 gainer (Falconer,
  Sculptor, Carpenter, Messenger, Quartermaster, Seaway) is also "+1 Card
  +1 Action". A Quartermaster that gains a Trail every turn starts each
  turn with a six-card hand.
- **Swamp Shacks** needs cards in play before it draws anything: three
  Trails or two Quartermasters plus itself is one card.
- **Barbarian** is the only attack and the main payload: +$2, and a
  Copper/Estate hit becomes a Curse for the victim.
- **Buys are scarce**: Messenger and Seaway's +1 Buy token are the only
  sources.

## Recommendation

The best strategy found is published as `Port Moresby Best Found`, defined
in `generated_strategies/port_moresby_best_found.py`.

This is not a formal proof of optimal play. It is the best strategy found
by the current simulator, hand-written seeds, island-model genetic
evolution, and focused local search around the leader.

The shape is Quartermaster money:

- Open Messenger and a Trail (turns 1-4), then buy Quartermasters with
  every $5 until you hold three (or the game passes turn 16 / four
  Provinces are gone), two Barbarians, and Gold. Silver only until turn
  12; Duchies from five Provinces left; Coppers up to ten for Fountain.
- Quartermaster gains follow the ordinary gain list: Silvers early, then
  Coppers once the Silver rule expires. Coppers gained this way sit on
  the mat, count for Fountain, and are never drawn.
- A Quartermaster takes a banked Silver into hand when the hand's Treasure
  plus $2 per Silver banked on that Quartermaster reaches $8 (one Silver
  per turn, so a $4 hand with two banked Silvers starts cashing them in),
  or when two or fewer Provinces remain. Otherwise it keeps gaining.
- Nothing ever trashes a Copper.

## Why This Strategy Wins

- **Quartermaster is the board's economy.** It stays in play for the
  whole game and either banks a free Silver or converts one into +$2 in
  hand on demand. Three of them turn a fat, untrashed money deck into a
  reliable Province machine; every island in the genetic run converged
  on multiple Quartermasters regardless of its seed.
- **Fountain for free.** Coppers gained onto the Quartermaster mat are
  owned but never drawn, so the 15 VP costs nothing in deck quality.
- **Engines do not get there.** Swamp Shacks needs three cards in play
  before it draws one, the only +Buy is Messenger, and Fountain punishes
  Copper trashing. Every engine seed (Falconer/Trail chains, Swamp
  Shacks/Daimyo, Quartermaster/Trail) lost to money before and after
  evolution; the engine islands themselves evolved into money.
- **Barbarian is the only attack worth playing.** +$2 with a Curse when
  it hits a Copper or Estate; two copies is the payload, and Daimyo
  doubling was measured flat.

## Method

1. **Audit** of the twelve implementations (fixes above).
2. **Archetype seeds** — seven hand-written theories of the kingdom in
   `dominion/strategy/strategies/port_moresby_seeds.py`: Barbarian money,
   Quartermaster money (one and two copies), Sculptor Fountain rush,
   Falconer/Trail engine, Swamp Shacks/Daimyo engine, Quartermaster/Trail
   engine, plus the hand-search leader `Port Moresby Copper Mat Money`.
3. **Hand local search on the Quartermaster policy** (eight rounds of
   100-200-game round robins): take-policy variants, Coppers-first onto
   the mat, Estates onto the mat, Barbarian count, greening timing,
   Secluded Shrine openers.
4. **Island-model genetic algorithm** — one island per seed plus Big
   Money, 30 generations, population 24, 16 games per evaluation, fixed
   panel (Big Money + the three strongest seeds).
5. **Champion tournament** (200 games/matchup), then grafting the hand
   Quartermaster policy onto the top champions and pruning their dead
   rules (200 games/round).
6. **Confirmation tournament** (400 games/matchup) and a 1,000-game
   head-to-head against the raw champion.

## Validation

Confirmation tournament, 400 games per matchup with alternating first
player. "Double Quartermaster Money Champion" is the raw island champion
the published strategy is built on; "Copper Mat Money" is the hand-search
leader before the genetic run; "Double Quartermaster Money" is the seed
the champion evolved from.

| Strategy | Average win rate |
|---|---:|
| Port Moresby Best Found (published) | 81.7% |
| Double Quartermaster Money Champion | 73.9% |
| Barbarian Money Champion | 67.7% |
| Copper Mat Money (hand leader) | 65.8% |
| Big Money Champion | 58.8% |
| Double Quartermaster Money (seed) | 35.4% |
| Big Money | 9.9% |
| Falconer Trail Engine (seed) | 6.8% |

Key head-to-heads (400 games per matchup with alternating first player,
except the first row, which is a separate 1,000-game run):

| Matchup | Result |
|---|---:|
| Best Found vs Double Quartermaster Money Champion (1,000 games) | 56.7% (+1.8 VP) |
| Best Found vs Barbarian Money Champion | 70.2% |
| Best Found vs Copper Mat Money | 70.8% |
| Best Found vs Double Quartermaster Money seed | 95.0% |
| Best Found vs Big Money | 100.0% |

The tables above predate three review fixes: each Quartermaster now keeps
its own set-aside pile (a second copy can no longer take the Silver the
first one just gained), those piles survive the endgame guard's cloned
state, and an off-turn Falconer gaining Messenger no longer triggers the
Buy-phase distribution. The island champions are not checked in, so the
confirmation tournament was not repeated; the checked-in opponents were,
400 games each with alternating first player:

| Matchup (after the fixes) | Result |
|---|---:|
| Best Found vs Copper Mat Money | 56.0% |
| Best Found vs Double Quartermaster Money seed | 94.8% |
| Best Found vs Barbarian Money seed | 98.0% |
| Best Found vs Falconer Trail Engine seed | 99.8% |
| Best Found vs Big Money | 100.0% |

The Copper Mat Money margin narrowed from 70.8% to 56.0%, most likely
because the shared mat had let Best Found's third Quartermaster cash in a
Silver the same turn another copy banked it.

## Search notes

- **The Quartermaster mat is the lever the genetic algorithm cannot
  reach.** The take/gain choice is an AI hook, not a priority rule. On
  the hand chassis, gaining three Coppers onto the mat first moved the
  leader from 56% to 85% in a 13-way round robin; on the evolved
  chassis the same rule *hurt* (43% vs 53%), because the champion already
  parks Coppers after its Silver rule expires and needs the early
  Quartermaster triggers for Silver income. The Province-gated take
  policy helped on both (62% vs 53% on the champion).
- **Every island converged on Quartermaster money.** The Barbarian Money
  island evolved into a strategy that buys neither Barbarian nor Gold
  (three Quartermasters, Silvers, Duchies from six Provinces left); the
  engine islands dropped their engines.
- **Pruning helped, openers did not.** Removing the champion's never-played
  Sculptor rule was worth about six points; removing its Messenger/Trail
  opener or its turn-12 Silver cap cost five to ten.
- **An early Secluded Shrine loses** (36-45% in a nine-way round robin):
  the Estates are not worth a tempo turn when Coppers must stay.
- **Falconer/Trail chains work in the simulator** (tested end to end) but
  the deck never assembles fast enough to matter against Quartermaster
  money on this board.
