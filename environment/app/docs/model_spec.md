# Meridian-2 directed lattice-relaxation model

This is the authoritative definition of the **structure** of the Meridian-2
relaxation model and of the **output contract**. It is a discrete-time dynamical
system on a two-dimensional integer lattice: load accumulates at lattice sites
and, wherever a site is overloaded, relaxes toward its south and east neighbours
until the field reaches a stable steady state. It is a **directed,
order-sensitive** cellular automaton — **not** the textbook four-neighbour
abelian sandpile — and, unlike the classical model, its steady state depends on
the order in which sites relax.

The exact numeric coefficients of the relaxation rule and the relaxation
schedule are **not fixed here**. They are calibrated constants, and the
authoritative record of their calibration is
`/app/docs/calibration_notebook.md`. This document fixes only the *form* of the
model and the *shape* of the output; the notebook fixes the numbers. See
"Calibrated parameters" below.

## Lattice and initial load

The initial load (`/app/data/drops.json`) has the shape:

```json
{ "rows": R, "cols": C, "drops": [[row, col, count], ...] }
```

Start from an `R x C` lattice of zeros (row indices `0..R-1` top to bottom,
column indices `0..C-1` left to right). Apply every deposit in order, adding
`count` units of load to site `(row, col)`. Deposits may target the same site
more than once.

## Relaxation rule (form)

A site is **overloaded** when its load reaches the calibrated *overload
threshold* `T`. The field is relaxed one event at a time according to the
calibrated *relaxation schedule*. A single relaxation event at a site whose load
at that moment is `c`:

* computes a **surge** `s = c // D`, where `D` is the calibrated *surge divisor*
  (integer division);
* removes `R_base + s` units from the site, where `R_base` is the calibrated
  *base removal*;
* transports `E` units **east** (to the site one column to the right), where `E`
  is the calibrated *eastward flux*;
* transports `Sth + s` units **south** (to the site one row below), where `Sth`
  is the calibrated *southward base flux*; the surge rides with the southward
  transport, never the eastward.

Load is only ever transported south and east — never north or west — so every
event drains toward the south-east and the field always converges. Load directed
off the lattice (east from the last column, or south from the last row) leaves
the domain and accumulates in the **spill** total.

Conservation holds by construction: `R_base + s` removed each event equals
`E + (Sth + s)` transported, so the calibrated fluxes must satisfy
`R_base = E + Sth`. Use this as a consistency check when you reconcile the
calibrated constants.

## Calibrated parameters

The following constants and the relaxation schedule are defined by the
calibration record in `/app/docs/calibration_notebook.md`, **not** here:

* `T` — overload threshold.
* `D` — surge divisor.
* `R_base` — base removal per event.
* `E` — eastward flux.
* `Sth` — southward base flux.
* the **relaxation schedule** — how the next site to relax is chosen and how many
  times it relaxes per event.

The notebook is a working calibration record: it contains early draft estimates
that were later revised. Reconcile it as an account that resolves over time —
**where a draft estimate and a later recalibration disagree, the later
recalibration governs** — and use the calibrated values that survive
reconciliation. Do not read or import anything from `/tests` or `/solution`.

## Steady-state observables (output contract)

Record the steady state in `result.json` in the output directory (`/app/output`
by default), with exactly these keys:

* `rows`, `cols` — copied from the input.
* `grid` — the steady-state lattice as a list of `R` rows, each a list of `C`
  integers, every value in `0 .. T-1`.
* `total_firings` — the total number of single relaxation events performed.
* `row_firings` — a list of `R` integers, the number of events in each row.
* `spill` — the total load that left the lattice.
* `grid_checksum` — the SHA-256 hex digest of the steady-state lattice
  serialized as follows: each row is its site values rendered in decimal and
  joined by single spaces; rows are joined by a single newline (`\n`); there is
  no trailing newline. Hash the UTF-8 encoding of that string.

The simulation reads its initial load from `--input` (default
`/app/data/drops.json`) and writes the steady-state observables under
`--output-dir` (default `/app/output`).
