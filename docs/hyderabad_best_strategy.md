# Hyderabad Board Strategy Search

Board: `boards/hyderabad.txt`

Kingdom:

- Ducat
- Scrap
- Stockpile
- Patron
- Priest
- River Shrine
- Village Green
- Rice Broker
- Scepter
- Scholar
- Project: Silos
- Way: Way of the Otter
- Prophecy: Progress (pinned — River Shrine is the Omen that deals it)

## Simulator fixes made before searching

A pre-search audit of all thirteen implementations found two rules bugs
that would have poisoned the search; both were fixed first (with tests):

1. **Scrap had a phantom +1 Action.** The real card is terminal. The
   phantom made any Scrap deck look strictly better than it is.
2. **The Exile gain rule was inverted.** Gaining a card used to *reclaim*
   one exiled copy instead of the gain (and restore the supply pile). The
   real Menagerie rule is that the gain always happens and the player may
   then discard **all** exiled copies of it. This single fix moved the
   Stockpile Rush seed from 4% to 93% vs Big Money: buying one Stockpile
   recalls the whole exiled battery, which is the engine that powers the
   winning strategy below.

This search also added `Prophecy:` support to board files. Without it,
any Omen board drew a random prophecy each game, so board evaluation was
non-stationary. Progress is pinned here.

Known remaining deviations that are acceptable on this board: Patron's
reveal reaction is dead code (nothing on this board reveals hand cards),
Scepter's replay choice is a hardcoded highest-cost heuristic, Silos
always discards every Copper, and Village Green never defers to next
turn. None of these is load-bearing for the recommended strategy.

## Recommendation

The best strategy found is published as `Hyderabad Best Found`, defined
in `generated_strategies/hyderabad_best_found.py`.

This is not a formal proof of optimal play. It is the best strategy
found by the current simulator, the seed archetypes, island-model
genetic evolution, and focused local search.

## Why This Strategy Wins

The board texture pushes hard toward disciplined money:

- **Progress topdecks every gain.** Treasure buys land on top of the
  deck and get drawn immediately — money decks accelerate. Green buys
  clog the next hand, which punishes early Duchy rushes and slow
  engines alike; Scholar's discard-and-draw-7 shrugs the clog off.
- **The Stockpile battery.** Stockpile is $3 with +1 Buy that Exiles
  itself on play. Under the corrected Exile rule, gaining a new
  Stockpile discards every exiled copy back into your deck, so one $3
  buy per turn recycles the entire fleet. With Progress active the new
  Stockpile also topdecks.
- **Way of the Otter and the weak engine pool.** The kingdom's draw
  (Scholar aside) is weak, and the Way lets any Action be +2 Cards, so
  there is no real engine payoff to race toward. Engine seeds (Village
  Green/Scholar, Rice Broker thinning, Priest payload) all lost badly
  to money archetypes.

The winning shape: open Silver/Scholar money, trash starting junk is
unnecessary (no cheap trasher fits), buy exactly one Scholar as draw,
build the Stockpile battery, take Gold over mid greening, and only
pivot to Duchy/Estate at the very end of the game (Progress makes early
green actively harmful).

## Method

1. **Audit** of the thirteen card/landscape implementations (fixes
   above).
2. **Archetype seeds** — seven hand-written theories of the kingdom
   (`dominion/strategy/strategies/hyderabad_seeds.py`): Scholar money,
   Village Green/Scholar engine, Priest payload, Stockpile rush, Otter
   Rice Broker engine, plus two hybrids.
3. **Island-model GA** — one isolated island per archetype plus Big
   Money, 40 generations each, identical hyperparameters, fixed
   opponent panel (Big Money + the three strongest seeds).
4. **Cross-island tournament** (300 games/matchup) to rank champions.
5. **Focused local search** around the tournament leader (Duchy/Estate
   timing, Scholar caps, Stockpile caps, pile-out awareness).
6. **Confirmation tournament** (400 games/matchup, top table below,
   plus a 1,000-game decisive head-to-head).

## Validation

Confirmation tournament, 400 games per matchup with alternating first
player. "Otter Pileout" is the published `Hyderabad Best Found` policy;
"Otter Champion" is the same policy without the pile-out Estate rule
(the raw island champion). "Combo Rush" and "Seed Stockpile Rush" are
the strongest hand-built falsifiers from the local search; neither was
part of the GA's fitness panel opponents for the winning island's final
form, which makes them useful out-of-sample checks.

| Strategy | Average win rate |
|---|---:|
| Otter Pileout (published) | 77.0% |
| Otter Champion | 71.1% |
| Stockpile Rush Champion | 56.4% |
| Combo Rush | 52.9% |
| Seed Stockpile Rush | 38.5% |
| Big Money | 4.2% |

Key head-to-heads:

| Matchup | Result |
|---|---:|
| Otter Pileout vs Otter Champion (1,000 games) | 58.6% |
| Otter Pileout vs Stockpile Rush Champion | 72.2% |
| Otter Pileout vs Combo Rush | 76.0% |
| Otter Pileout vs Seed Stockpile Rush | 86.0% |
| Otter Pileout vs Big Money | 96.8% |

The published file was replayed against the raw tournament variant as a
sanity check (49.0% over 400 games — a statistical mirror) before
publication.

## Search notes

- Every island's GA independently abandoned its seed archetype and
  converged on the same Province-first money chassis; the islands only
  differed in whether they kept the Stockpile battery. The two that did
  (Stockpile Rush, Otter Broker) finished first and second.
- The engine seeds are not close: the best engine (Village
  Green/Scholar) lost 0-for-100 to the seed Stockpile Rush before
  evolution. Progress's topdecked green and the absence of cheap
  trashing appear to bury engines on this board.
- The one hand-found improvement the GA missed — Estates on two empty
  piles — is a three-pile-ending rule. The GA's fitness panel could not
  teach it because none of the panel opponents contested piles.
- The island merge stage was not run for this search (the initial
  attempt was cancelled); the local search around the tournament leader
  stood in for it.
- Earlier hand probes of pure-rush thresholds (Duchy at ≤6 provinces
  left, Estates from ≤6, Gold in the mix) all fell to the champion line
  and were discarded rather than published.
