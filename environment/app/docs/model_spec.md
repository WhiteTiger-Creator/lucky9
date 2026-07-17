# Meridian-2 directed lattice-relaxation model

This is the authoritative definition of the Meridian-2 relaxation model: a
discrete-time dynamical system on a two-dimensional integer lattice. Load
accumulates at lattice sites and, wherever a site is overloaded, relaxes toward
its south and east neighbours until the field reaches a stable steady state. It
is a **directed, order-sensitive** cellular automaton — **not** the textbook
four-neighbour abelian sandpile — and, unlike the classical model, its steady
state depends on the order in which sites relax, so the relaxation schedule
below is part of the model.

## Lattice and initial load

The initial load (`/app/data/drops.json`) has the shape:

```json
{ "rows": R, "cols": C, "drops": [[row, col, count], ...] }
```

Start from an `R x C` lattice of zeros (row indices `0..R-1` top to bottom,
column indices `0..C-1` left to right). Apply every deposit in order, adding
`count` units of load to site `(row, col)`. Deposits may target the same site
more than once.

## Relaxation schedule (mandated order)

A site is **overloaded** when it holds 4 or more units. Relaxation proceeds one
event at a time, in a fixed order:

1. Among all currently overloaded sites, select the one with the smallest
   `(row, col)` in lexicographic order (smallest row first, then smallest
   column).
2. **Relax that site exactly once** (see the relaxation rule below).
3. Repeat until no overloaded sites remain.

The dynamics are **not** order-independent: relaxing greedily (draining a site
in one event), or relaxing sites in any other order, yields a different steady
state. Relax exactly one site, exactly once, per event, always choosing the
smallest index.

## Relaxation rule (one event)

Let `c` be the load on the site **at the moment it relaxes**, and let the
**surge** be `s = c // 8` (integer division). One relaxation event:

* removes `4 + s` units from the site,
* transports **2 units east** (to the site one column to the right), and
* transports **2 + s units south** (to the site one row below).

The surge flows entirely south; the eastward flux is always exactly 2. Because
`s` depends on the site's load at relaxation time, and that load depends on flux
delivered by earlier events, the schedule above is what makes the steady state
well-defined.

Load directed off the lattice — east from the last column, or south from the
last row — leaves the domain and accumulates in the **spill** total. Load is
never transported north or west, so every event drains toward the south-east
and the field always converges.

## Steady-state observables

Record the steady state in `result.json` in the output directory (`/app/output`
by default), with exactly these keys:

* `rows`, `cols` — copied from the input.
* `grid` — the steady-state lattice as a list of `R` rows, each a list of `C`
  integers, every value in `0..3`.
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
