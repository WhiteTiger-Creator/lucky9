# Meridian SE-draining chip-firing model

This is the authoritative definition of the Meridian stabilization model. It is
a directed variant of abelian chip-firing; it is **not** the textbook
four-neighbour sandpile, and an implementation of the textbook rule will not
reproduce these results.

## Grid and drops

The input (`/app/data/drops.json`) has the shape:

```json
{ "rows": R, "cols": C, "drops": [[row, col, count], ...] }
```

Start from an `R x C` grid of zeros (row indices `0..R-1` top to bottom, column
indices `0..C-1` left to right). Apply every drop in order, adding `count` chips
to cell `(row, col)`. Drops may target the same cell more than once.

## Firing rule

A cell is **unstable** when it holds 4 or more chips. Stabilization repeatedly
fires unstable cells until none remain. One firing of a cell:

* removes exactly 4 chips from the cell, and
* sends **2 chips east** (to the cell one column to the right) and
  **2 chips south** (to the cell one row below).

Chips directed off the grid — east from the last column, or south from the last
row — leave the grid and are accumulated in the **spill** total. Chips are never
sent north or west.

Because every cell drains toward the south-east and off the grid, stabilization
always terminates, and the final grid, the firing counts, and the spill are
independent of the order in which unstable cells are fired.

## Output

Write `result.json` to the output directory (default `/app/output`) with
exactly these keys:

* `rows`, `cols` — copied from the input.
* `grid` — the stabilized grid as a list of `R` rows, each a list of `C`
  integers, every value in `0..3`.
* `total_firings` — the total number of firings across all cells.
* `row_firings` — a list of `R` integers, the number of firings in each row.
* `spill` — the total chips that left the grid.
* `grid_checksum` — the SHA-256 hex digest of the stabilized grid serialized as
  follows: each row is its cell values rendered in decimal and joined by single
  spaces; rows are joined by a single newline (`\n`); there is no trailing
  newline. Hash the UTF-8 encoding of that string.

The command-line interface is `--input PATH` (default `/app/data/drops.json`)
and `--output-dir PATH` (default `/app/output`).
