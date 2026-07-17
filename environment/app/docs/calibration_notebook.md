# Meridian-2 calibration notebook

Working record of the Meridian-2 lattice-relaxation calibration. Entries are in
rough chronological order; the February entries are the first-pass fit against
the small validation lattice and several were revised during the May
recalibration once the wider validation set was in place. **Where a February
draft estimate and a later recalibration disagree, the later recalibration
governs.** Most of this notebook is routine run logging; the constants that
matter are `T` (overload threshold), `D` (surge divisor), `R_base` (base
removal), `E` (eastward flux), `Sth` (southward base flux), and the relaxation
schedule.

---

### CAL-2402-01 (2026-02-03, Aritra) — first validation lattice

Cut a 6×6 validation lattice `V0` with a single hot corner and hand-traced the
first few relaxations to sanity-check the directed drain. Confirms the field
only ever moves load south and east; nothing flows back north or west. No
constants fixed yet.

### CAL-2402-04 (2026-02-05, Aritra) — threshold, first pass

Fitting the onset of relaxation against `V0`, a site looks stable until it holds
five units, so we take the overload threshold `T = 5` for now. *(Superseded —
see the May recalibration CAL-2405-06, which refits `T` against the full
validation set.)*

### CAL-2402-09 (2026-02-08, Priya) — surge onset

The heavy-corner runs need a nonlinear term or the corner drains too slowly. A
surge `s = c // 6` (divisor `D = 6`) tracks the observed corner decay on `V0`
adequately. Flagging `D` for refit — the 6 is eyeballed off a single lattice.
*(Superseded — see CAL-2405-08.)*

### CAL-2402-10 (2026-02-08, Priya) — removal, first pass

With the surge in, the simplest bookkeeping is to have a relaxing site shed
exactly the threshold and let the surge ride out in transport only, i.e. remove
`T` units per event. *(Superseded — the May recalibration CAL-2405-09 reworks
the removal so the field conserves load; see there.)*

### CAL-2402-14 (2026-02-11, Aritra) — routine run log

Batch of 40 randomized `V0` initialisations to profile convergence. All
terminated; median 210 events. Nothing to fix, recorded for the run history.

### CAL-2402-15 (2026-02-12, Priya) — transport split, first pass

First-pass transport: one unit east, the rest south. So `E = 1`, and the
southward base takes the remainder. This under-weights the eastward drain on the
wide lattices and is revised in May. *(Superseded — see CAL-2405-10.)*

### CAL-2402-18 (2026-02-15, Priya) — surge routing, first pass

Tried splitting the surge evenly between the east and south neighbours (half the
surge each, rounded). It smears the corner signature and made the `V0` trace
ambiguous. Marked for revisit. *(Superseded — see CAL-2405-11, which routes the
whole surge south.)*

### CAL-2402-22 (2026-02-19, Aritra) — schedule, first pass

For the first fit we swept the lattice in row-major order (row 0 left→right, then
row 1, …), relaxing every site that was overloaded once per sweep, and repeated
sweeps until no site was overloaded. Easy to implement, but the sweep order left
a visible dependence on lattice width that we could not reconcile against the
hand traces. *(Superseded — see CAL-2405-14, the governing schedule.)*

### CAL-2402-23 (2026-02-20, Aritra) — schedule, alternative tried

Also tried draining each overloaded site fully (relax it repeatedly until it
fell below threshold) before moving to the next site. This diverged further from
the traces than the row-major sweep. Rejected. *(Superseded — see CAL-2405-14.)*

---

## May 2026 recalibration

Rebuilt the validation set (added the 12×12 `V2` and the asymmetric `V3`) and
refit every constant. The entries below are the governing values unless a later
May entry revises them in turn.

### CAL-2405-06 (2026-05-04, Nadia) — overload threshold, refit

Against the full validation set the relaxation onset sits at four units, not
five: a site is overloaded once it holds four or more. **`T = 4`.** Supersedes
CAL-2402-04.

### CAL-2405-08 (2026-05-05, Nadia) — surge divisor, refit

Refitting the corner-decay term across `V2`/`V3` moves the divisor off the
February value. The corner traces are matched by `s = c // 8`. **`D = 8`.**
Supersedes CAL-2402-09. (We did trial `D = 10` on `V3` alone; it under-drove the
corner on `V2` and was rejected — keep `D = 8`.)

### CAL-2405-09 (2026-05-06, Ilya) — base removal, reworked for conservation

The February "shed the threshold" rule (CAL-2402-10) does not conserve load once
the surge is transported, which showed up as drift in the `V2` totals. Rework:
each event removes a fixed base plus the surge, `R_base + s`, with the base set
so that removal equals total transport. With the transport fixed below
(`E + Sth`), the base is **`R_base = 4`**. Supersedes CAL-2402-10.

### CAL-2405-10 (2026-05-06, Ilya) — eastward flux, refit

The February one-unit east drain (CAL-2402-15) under-weighted the eastward
spread on the wide `V2`. Refit gives **`E = 2`** units transported east per
event. Supersedes CAL-2402-15.

### CAL-2405-11 (2026-05-07, Ilya) — southward base flux and surge routing

The even surge split (CAL-2402-18) is out. The whole surge rides south. The
southward transport is a base of **`Sth = 2`** units plus the entire surge, so a
site sends `2 + s` south while the east neighbour always receives exactly `E`.
Supersedes CAL-2402-18. Check: `R_base = E + Sth = 2 + 2 = 4`, matching
CAL-2405-09, so the field conserves load.

### CAL-2405-12 (2026-05-07, Nadia) — routine validation

Re-ran `V0`/`V2`/`V3` end-to-end with the refit constants; steady states match
the hand traces to the site. Conservation residual is zero across all three.
Recorded for the run history; fixes nothing further.

### CAL-2405-14 (2026-05-08, Nadia) — relaxation schedule, governing

The row-major sweep (CAL-2402-22) and the drain-in-place variant (CAL-2402-23)
both failed to reproduce the traces because this model is order-sensitive and
neither order is the physical one. The governing schedule is single-event and
index-ordered:

1. Among all currently overloaded sites, take the one with the smallest
   `(row, column)` in lexicographic order (smallest row first, then smallest
   column).
2. Relax that site **exactly once** (one event, per the relaxation rule).
3. Repeat from step 1 until no site is overloaded.

A site is not drained in one visit; if it is still overloaded after an event it
simply becomes eligible again on a later step. Supersedes CAL-2402-22 and
CAL-2402-23. This schedule is final.

### CAL-2405-17 (2026-05-10, Nadia) — sign-off

Full validation set reproduced with the refit constants and the governing
schedule; conservation residual zero on every lattice. All calibration items
from the February pass are now closed by their May recalibration entries above.
No open items.
