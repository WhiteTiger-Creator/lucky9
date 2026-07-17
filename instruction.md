The stabilizer at `/app/stabilize.py` is still running the old four-neighbour sandpile rule and no longer matches the Meridian model, so its firing counts and grids come out wrong. Bring it in line with the current model.

`/app/docs/model_spec.md` defines the Meridian SE-draining chip-firing model precisely. Rewrite `/app/stabilize.py` so that, given the drops in `/app/data/drops.json`, it stabilizes the grid under that model and writes `result.json` to the output directory with every field the spec lists — the stabilized grid, `total_firings`, `row_firings`, `spill`, and the `grid_checksum` computed with the exact serialization the spec describes. Keep the `--input` and `--output-dir` flags and their defaults.

Run it when you are done so `/app/output/result.json` is in place. Derive everything from the input; don't read or import anything from `/tests` or `/solution`.
