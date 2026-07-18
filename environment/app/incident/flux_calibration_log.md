# Meridian-2 Transport Model — Calibration Review Log
Meridian-2 transport group — calibration archive for the sustained-flux observable (2026-Q1 through 2026-Q2).

## Summary
The transport estimator produced unphysical sustained-flux values after the February model rollout. How the observable is *meant* to be evaluated — link conditioning and validity bounds, the channel span bound, the sustained-flux objective, the deterministic tie-broken routed channel set, the residual packing, and the per-hop efficiency aggregates — was fixed incrementally by the model review board, and those calibration decisions live in the review entries below, not in any single summary. The February draft parameterizations were revisited in the 2026-05 calibration cycle and several were reversed; where a draft and a later calibration decision disagree, the later decision governs, and where a decision was itself revised by a still-later one, the latest dated decision is binding — trace each rule to its final entry. `/app/docs/model_spec.md` is the output contract only: it fixes the network input shape, the exact `result.json` key set, and the byte-level checksum serialization — not how the values are derived.

## February Draft Parameterizations (2026-02 — partly reversed)
The initial rollout circulated model-behavior drafts through MX tickets in the 1900 range. Several did not survive calibration review; they are archived in place below and marked superseded — do not implement them as written.

### Review entry 0001 — conditioning bench
> **Model draft (2026-02-05 - MX-1902)** Rao: link weights are valid in the range 1..7; links outside that range are discarded. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Bench run logged nominal transport on the calibration lattice; instrument drift attributed to probe warm-up, not the estimator.

### Review entry 0002 — conditioning bench
> **Model draft (2026-02-08 - MX-1905)** Rao: when a directed link (source,target) is repeated, keep the FIRST occurrence encountered and discard later duplicates. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Analysts should reconcile behavior questions against the MX calibration entries rather than lab-notebook excerpts.

### Review entry 0003 — span bench
> **Model draft (2026-02-11 - MX-1908)** Sole: transport channels are simple directed paths of at most THREE links from the source. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
No estimator semantics changed in this entry; parameters remain as approved by the board.

### Review entry 0004 — objective bench
> **Model draft (2026-02-14 - MX-1911)** Sole: the sustained flux is the SUM over reachable sites of each site's strongest single channel flux. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Historical CSV exports remain archived and non-authoritative for the JSON result acceptance.

### Review entry 0005 — objective bench
> **Model draft (2026-02-17 - MX-1914)** Iyer: the sustained flux is evaluated greedily — repeatedly commit the strongest still-vertex-disjoint channel; that greedy total is the reported flux. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Thread archived; see the MX calibration entries for anything affecting estimator behavior.

### Review entry 0006 — selection bench
> **Model draft (2026-02-20 - MX-1917)** Iyer: when the objective admits more than one optimal channel set, report ANY one of them; the routed set need not be canonical. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Bench run logged nominal transport; no calibration-relevant findings for this lane.

### Review entry 0007 — flux bench
> **Model draft (2026-02-23 - MX-1920)** Sole: a channel's flux is its bottleneck conductance — the MINIMUM edge weight along the channel (a series-conductance reading). *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Bench run logged nominal transport; the series-vs-additive question was escalated to the 2026-05 cycle.

## Calibration Review Archive (2025-Q4 through 2026-Q2)
Routine entries are context only. MX-ticketed draft and decision quotes embedded in the entries are the authoritative record for estimator behavior.

### Review entry 0021 — span bench
> **Calibration decision (2026-04-08 - MX-2104)** Priya: transport channels are simple directed paths of at most FOUR links from the source. *(Revised — see the 2026-05 calibration.)*
Bench run logged nominal transport; rotation swap approved, no parameter change.

### Review entry 0022 — selection bench
> **Calibration decision (2026-04-12 - MX-2108)** Priya: among optimal channel sets, prefer the one assembled by taking channels in ascending path-sequence order (a greedy smallest-sequence-first construction). *(Revised — see the 2026-05 calibration.)*
Analysts should reconcile behavior questions against the MX calibration entries rather than lab-notebook excerpts.

### Review entry 0023 — residual bench
> **Calibration decision (2026-04-16 - MX-2112)** Dana: the residual flux is the best packing over the channels whose site sets are entirely disjoint from the routed set's sites. *(Revised — see the 2026-05 calibration.)*
No estimator semantics changed in this entry; parameters remain as approved by the board.

### Review entry 0024 — efficiency bench
> **Calibration decision (2026-04-20 - MX-2116)** Dana: a channel's per-hop efficiency is its flux (no division by hop count); `total_path_efficiency` sums channel flux over the routed set and `max_path_efficiency` is the largest channel flux. *(Revised — see the 2026-05 calibration.)*
Thread archived; see the MX calibration entries for anything affecting estimator behavior.

### Review entry 0025 — efficiency bench
> **Calibration decision (2026-04-24 - MX-2120)** Dana: `mean_flux_floor` is the sustained flux divided by the routed channel count, rounded to the nearest integer. *(Revised — see the 2026-05 calibration.)*
Bench run logged nominal transport; no calibration-relevant findings for this lane.

### Review entry 0031 — conditioning bench
> **Calibration decision (2026-05-03 - MX-2201)** Ilya: link conditioning — discard self-loops (source==target) and links whose weight is outside the inclusive range 1..9; when a directed link (source,target) repeats, collapse the duplicates keeping the MAXIMUM weight. This supersedes MX-1902 and MX-1905.

### Review entry 0032 — span bench
> **Calibration decision (2026-05-04 - MX-2202)** Ilya: transport channels are simple directed paths of one to FIVE links (inclusive) starting at the source (site 0); a simple path repeats no site. This supersedes MX-1908 and MX-2104.

### Review entry 0032b — flux bench
> **Calibration decision (2026-05-05 - MX-2204)** Ilya: a channel's flux is ADDITIVE — the SUM of the conductance weights of its constituent edges, accumulated along the channel from the source. It is not the bottleneck/minimum edge weight. Every flux-valued quantity (a channel's flux, `strongest_path_weight`, `max_flux`, and the routed channels' fluxes) uses this additive sum. This supersedes MX-1920.

### Review entry 0033 — objective bench
> **Calibration decision (2026-05-06 - MX-2203)** Ilya: the sustained flux `max_flux` is the exact maximum total weight of a set of VERTEX-DISJOINT channels (channels sharing only the source). It is NOT the per-site sum of strongest channels (that over-counts shared sites) and NOT a greedy strongest-first value (greedy is not optimal). The empty set carries 0. This supersedes MX-1911 and MX-1914.

### Review entry 0034 — selection bench
> **Calibration decision (2026-05-08 - MX-2205)** Marta: the routed set is selected deterministically. First reduce each channel to its non-source site set and, for each distinct site set, keep the representative channel of greatest flux, breaking equal flux by the lexicographically smallest full site sequence. Then, among ALL vertex-disjoint selections of representatives whose total flux equals `max_flux`, choose the selection whose representative site sequences, sorted ascending, form the lexicographically smallest tuple. This is a tie-break over whole selections, not a greedy per-channel choice: consider every selection attaining the maximum, then take the lexicographically least. `flux_paths` lists that selection's channels (each a site-id list from the source), sorted ascending. This supersedes MX-1917 and MX-2108.

### Review entry 0035 — residual bench
> **Calibration decision (2026-05-10 - MX-2207)** Marta: the residual packing re-runs the identical vertex-disjoint objective over only the representative channels NOT in the routed set (identified by site set); `residual_flux` is that packing's total (0 if none remain). The representatives that lost the tie-break contend among themselves, so this is a genuine second packing — it is NOT restricted to channels disjoint from the routed set's sites. This supersedes MX-2112.

### Review entry 0036 — efficiency bench
> **Calibration decision (2026-05-12 - MX-2209)** Nadia: a channel's per-hop efficiency is its flux INTEGER-DIVIDED (floored) by its hop count (number of links). `total_path_efficiency` sums the floored per-hop efficiency over the routed channels; `max_path_efficiency` is the largest floored per-hop efficiency (0 if none). This supersedes MX-2116.

### Review entry 0037 — efficiency bench
> **Calibration decision (2026-05-13 - MX-2211)** Nadia: `mean_flux_floor` = `max_flux // flux_path_count` (integer floor division), and 0 when the routed set is empty. This supersedes MX-2120.

### Review entry 0026b — throughput bench
> **Model draft (2026-02-25 - MX-1922)** Sole: throughput ledger — process the routed channels in `flux_paths` order; carry_in = max(previous carry_out - (hops * 5) // 2, 0); throughput = channel_flux + carry_in // 3; carry_out = min(carry_in + channel_flux, 50); a channel is saturated when throughput >= 16. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Bench run logged nominal transport; the decay/credit divisors were escalated to the 2026-05 cycle.

### Review entry 0039 — throughput bench
> **Calibration decision (2026-05-15 - MX-2213)** Nadia: throughput ledger (final) — process the routed channels in `flux_paths` order; carry starts at 0. For each channel: `hops` is its edge count and `channel_flux` its additive flux (per MX-2204); `carry_in = max(previous_carry_out - (hops * 5) // 3, 0)`; `throughput = channel_flux + carry_in // 4`; `carry_out = min(carry_in + channel_flux - (hops // 2), 60)`; a channel is admitted to the saturated set when `throughput >= 20`. `saturated_endpoints` are the terminal site ids of saturated channels, sorted ascending; `saturated_channel_count` is their number; `max_throughput` is the maximum throughput over the routed channels. The `*5`/`//3` decay, the `//4` credit, the 60 cap and the 20 threshold are final and revise MX-1922. This supersedes MX-1922.

### Review entry 0041 — audit bench
Bench run logged nominal transport; quarterly recertification touched this lane, no estimator-relevant configuration changed.

### Review entry 0042 — audit bench
> **Calibration decision (2026-05-24 - MX-2240)** Priya: calibration dashboards retain ninety days of run history; older runs are served from the archive on demand. Dashboard retention is an operational setting and carries no weight in the estimator output.
