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

### Review entry 0008 — conditioning bench
> **Model draft (2026-02-26 - MX-1925)** Rao: site conditioning — damping values are valid in the range 0..8; when a site is listed more than once, keep the FIRST occurrence and discard later repeats. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Probe technicians noted the conditioning bench was recalibrated mid-run; the damping ledger was re-zeroed afterwards and the affected shift discarded.

### Review entry 0009 — damping bench
> **Model draft (2026-03-01 - MX-1928)** Sole: a channel's damped flux subtracts the accumulated site damping in FULL — `damped_flux = channel_flux - damping_sum`, floored at zero. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
The full-subtraction form drove several lattice channels to zero and was flagged by the transport group as unphysical for the sustained observable.

### Review entry 0010 — dispatch bench
> **Model draft (2026-03-04 - MX-1931)** Iyer: every routed channel is dispatched; there is no admission floor and no dispatch class. *(Superseded — reversed in the 2026-05 calibration; see the matching decision.)*
Downstream consumers reported that undifferentiated dispatch made the transport ledger unusable for capacity planning.

## Calibration Review Archive (2025-Q4 through 2026-Q2)
Routine entries are context only. MX-ticketed draft and decision quotes embedded in the entries are the authoritative record for estimator behavior.

### Review entry 1003 — selection bench
Iyer on shift. Recertification paperwork for the calibration lattice was renewed. No parameters changed and no estimator behaviour is implicated. Parameters remain as approved by the board.

### Review entry 1010 — damping bench
Lindqvist on shift. An external group asked for the raw sweep archive. The request was met with the published archive; the estimator configuration was not shared as it is unreleased. Bench run logged nominal transport for this lane.

### Review entry 1017 — span bench
Dana on shift. Two channels on the east lattice reported intermittent conductance; the harness was reterminated and the fault did not recur across a 12-hour soak. Filed for the recertification record; no calibration impact.

### Review entry 1024 — throughput bench
Halvorsen on shift. The lattice was re-levelled following the floor survey. Post-survey transport readings reproduced the pre-survey reference set. Referred to the tooling backlog; no model impact.

### Review entry 1031 — lattice bench
Marta on shift. Cryostat pressure drifted 0.4% over the shift. Transport readings were unaffected, but the shift log was annotated for the recertification file. Closed with no action required.

### Review entry 1038 — residual bench
Sole on shift. Network capture during the overnight sweep showed a retransmission burst on the acquisition link. Data integrity checks passed and the sweep was retained. No estimator semantics changed in this entry.

### Review entry 1045 — audit bench
Okafor on shift. A visiting reviewer noted the archive index was stale by one cycle. The index was rebuilt; no underlying records changed. Parameters remain as approved by the board.

### Review entry 1052 — objective bench
Priya on shift. A junior analyst's reconstruction disagreed with the reference by one unit; the discrepancy was traced to a stale local checkout, not the estimator. Bench run logged nominal transport for this lane.

### Review entry 1059 — dispatch bench
Baptiste on shift. A question was raised about whether retired draft parameterizations should be deleted from this log. The board elected to retain them in place, marked superseded. Filed for the recertification record; no calibration impact.

### Review entry 1066 — conditioning bench
Ilya on shift. A duplicated row in the shift handover sheet was traced to a copy-paste during the handover and corrected in the source spreadsheet. Referred to the tooling backlog; no model impact.

### Review entry 1073 — efficiency bench
Rao on shift. A reporting script was rewritten to stream rather than buffer the archive. Output bytes were verified identical against the previous implementation. Closed with no action required.

### Review entry 1080 — probe bench
Nadia on shift. An analyst asked whether the dashboards could show per-shift transport medians. The request was logged as a reporting feature, not a model change. No estimator semantics changed in this entry.

### Review entry 1087 — selection bench
Iyer on shift. Thermal cycling on the north bench produced a transient conductance step. The step did not persist and was attributed to a connector, since replaced. Parameters remain as approved by the board.

### Review entry 1094 — damping bench
Lindqvist on shift. The archive export job overran its window because of a slow storage mount. No estimator inputs were touched; the job was rescheduled off-peak. Bench run logged nominal transport for this lane.

### Review entry 1101 — span bench
Dana on shift. Quarterly access review completed for the calibration share. Two dormant accounts were removed; no configuration was altered. Filed for the recertification record; no calibration impact.

### Review entry 1108 — throughput bench
Halvorsen on shift. A vendor firmware note changed the sampling window default; the bench was pinned to the previous window and the change deferred to the next cycle. Referred to the tooling backlog; no model impact.

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

### Review entry 0026 — conditioning bench
> **Calibration decision (2026-04-26 - MX-2124)** Dana: site damping outside the valid range is CLAMPED into range (values above the maximum become the maximum) rather than discarded. *(Revised — see the 2026-05 calibration.)*
Lattice recertification completed on the conditioning bench; no probe replacements were required this cycle.

### Review entry 0027 — damping bench
> **Calibration decision (2026-04-28 - MX-2128)** Dana: the accumulated site damping is HALVED with integer floor division before subtraction — `damped_flux = max(channel_flux - damping_sum // 2, 0)`. *(Revised — see the 2026-05 calibration.)*
The halving was introduced to keep conditioned channels on-scale; the rounding direction was left open pending the 2026-05 cycle.

### Review entry 0028 — dispatch bench
> **Calibration decision (2026-04-30 - MX-2132)** Priya: the hop attenuation applied after damping is `hops * 2`. *(Revised — see the 2026-05 calibration.)*
Bench comparison against the reference lattice showed the linear form over-attenuated long channels.

### Review entry 0029 — dispatch bench
> **Calibration decision (2026-05-01 - MX-2136)** Priya: dispatch admission floor is 5 on the conditioned flux, and dispatched channels carry one of TWO classes, `primary` and `secondary`. *(Revised — see the 2026-05 calibration.)*
Capacity planning asked for a third tier to separate marginal channels; deferred to the mid-May cycle.

### Review entry 0030 — dispatch bench
> **Calibration decision (2026-05-02 - MX-2140)** Priya: dispatched channels are reported in ascending terminal-site order. *(Revised — see the 2026-05 calibration.)*
Ordering by site id was convenient for the dashboards but carried no capacity semantics.

### Review entry 1115 — lattice bench
Marta on shift. A proposal to cache intermediate channel enumerations was reviewed. It changes runtime only and carries no estimator semantics; approved for the tooling backlog. Closed with no action required.

### Review entry 1122 — residual bench
Sole on shift. Probe A7 was re-seated after a warm-up excursion; the affected sweep was rerun and the replacement trace matched the reference lattice within tolerance. No estimator semantics changed in this entry.

### Review entry 1129 — audit bench
Okafor on shift. The spare probe inventory was audited. Two units were retired for drift and replaced from stores; calibration constants were re-derived for the new units. Parameters remain as approved by the board.

### Review entry 1136 — objective bench
Priya on shift. The acquisition host was patched during the maintenance window. Post-patch verification reproduced the reference sweep byte for byte. Bench run logged nominal transport for this lane.

### Review entry 1143 — dispatch bench
Baptiste on shift. Bench timing was resynchronised against the site clock after a leap-second advisory. Transport observables are not time-referenced and were unaffected. Filed for the recertification record; no calibration impact.

### Review entry 1150 — conditioning bench
Ilya on shift. Humidity control on the enclosure was serviced. The service window overlapped one sweep, which was discarded and repeated the following shift. Referred to the tooling backlog; no model impact.

### Review entry 1157 — efficiency bench
Rao on shift. Ambient magnetic shielding was re-measured after building works. Values remained inside the acceptance envelope for the transport bench. Closed with no action required.

### Review entry 1164 — probe bench
Nadia on shift. The shift rota changed to accommodate the recertification window. No bench parameters were touched during the transition. No estimator semantics changed in this entry.

### Review entry 1171 — selection bench
Iyer on shift. Recertification paperwork for the calibration lattice was renewed. No parameters changed and no estimator behaviour is implicated. Parameters remain as approved by the board.

### Review entry 1178 — damping bench
Lindqvist on shift. An external group asked for the raw sweep archive. The request was met with the published archive; the estimator configuration was not shared as it is unreleased. Bench run logged nominal transport for this lane.

### Review entry 1185 — span bench
Dana on shift. Two channels on the east lattice reported intermittent conductance; the harness was reterminated and the fault did not recur across a 12-hour soak. Filed for the recertification record; no calibration impact.

### Review entry 1192 — throughput bench
Halvorsen on shift. The lattice was re-levelled following the floor survey. Post-survey transport readings reproduced the pre-survey reference set. Referred to the tooling backlog; no model impact.

### Review entry 1199 — lattice bench
Marta on shift. Cryostat pressure drifted 0.4% over the shift. Transport readings were unaffected, but the shift log was annotated for the recertification file. Closed with no action required.

### Review entry 1206 — residual bench
Sole on shift. Network capture during the overnight sweep showed a retransmission burst on the acquisition link. Data integrity checks passed and the sweep was retained. No estimator semantics changed in this entry.

### Review entry 1213 — audit bench
Okafor on shift. A visiting reviewer noted the archive index was stale by one cycle. The index was rebuilt; no underlying records changed. Parameters remain as approved by the board.

### Review entry 1220 — objective bench
Priya on shift. A junior analyst's reconstruction disagreed with the reference by one unit; the discrepancy was traced to a stale local checkout, not the estimator. Bench run logged nominal transport for this lane.

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
> **Calibration decision (2026-05-15 - MX-2213)** Nadia: throughput ledger (final) — process the routed channels in `flux_paths` order; carry starts at 0. For each channel: `hops` is its edge count and `channel_flux` its additive flux (per MX-2204); `carry_in = max(previous_carry_out - (hops * 5) // 3, 0)`; `throughput = channel_flux + carry_in // 4`; `carry_out = min(carry_in + channel_flux - (hops // 2), 60)`; a channel is admitted to the saturated set when `throughput >= 20`. `saturated_endpoints` are the terminal site ids of saturated channels, sorted ascending; `saturated_channel_count` is their number; `max_throughput` is the maximum throughput over the routed channels. The `*5`/`//3` decay, the `//4` credit, the 60 cap and the 20 threshold are final and revise MX-1922. This supersedes MX-1922. ROUNDING: carry_in // 4 = FLOOR. ROUNDING: hops // 2 = FLOOR.

### Review entry 1227 — dispatch bench
Baptiste on shift. A question was raised about whether retired draft parameterizations should be deleted from this log. The board elected to retain them in place, marked superseded. Filed for the recertification record; no calibration impact.

### Review entry 1234 — conditioning bench
Ilya on shift. A duplicated row in the shift handover sheet was traced to a copy-paste during the handover and corrected in the source spreadsheet. Referred to the tooling backlog; no model impact.

### Review entry 1241 — efficiency bench
Rao on shift. A reporting script was rewritten to stream rather than buffer the archive. Output bytes were verified identical against the previous implementation. Closed with no action required.

### Review entry 1248 — probe bench
Nadia on shift. An analyst asked whether the dashboards could show per-shift transport medians. The request was logged as a reporting feature, not a model change. No estimator semantics changed in this entry.

### Review entry 1255 — selection bench
Iyer on shift. Thermal cycling on the north bench produced a transient conductance step. The step did not persist and was attributed to a connector, since replaced. Parameters remain as approved by the board.

### Review entry 1262 — damping bench
Lindqvist on shift. The archive export job overran its window because of a slow storage mount. No estimator inputs were touched; the job was rescheduled off-peak. Bench run logged nominal transport for this lane.

### Review entry 1269 — span bench
Dana on shift. Quarterly access review completed for the calibration share. Two dormant accounts were removed; no configuration was altered. Filed for the recertification record; no calibration impact.

### Review entry 1276 — throughput bench
Halvorsen on shift. A vendor firmware note changed the sampling window default; the bench was pinned to the previous window and the change deferred to the next cycle. Referred to the tooling backlog; no model impact.

### Review entry 1283 — lattice bench
Marta on shift. A proposal to cache intermediate channel enumerations was reviewed. It changes runtime only and carries no estimator semantics; approved for the tooling backlog. Closed with no action required.

### Review entry 1290 — residual bench
Sole on shift. Probe A7 was re-seated after a warm-up excursion; the affected sweep was rerun and the replacement trace matched the reference lattice within tolerance. No estimator semantics changed in this entry.

### Review entry 1297 — audit bench
Okafor on shift. The spare probe inventory was audited. Two units were retired for drift and replaced from stores; calibration constants were re-derived for the new units. Parameters remain as approved by the board.

### Review entry 1304 — objective bench
Priya on shift. The acquisition host was patched during the maintenance window. Post-patch verification reproduced the reference sweep byte for byte. Bench run logged nominal transport for this lane.

### Review entry 1311 — dispatch bench
Baptiste on shift. Bench timing was resynchronised against the site clock after a leap-second advisory. Transport observables are not time-referenced and were unaffected. Filed for the recertification record; no calibration impact.

### Review entry 1318 — conditioning bench
Ilya on shift. Humidity control on the enclosure was serviced. The service window overlapped one sweep, which was discarded and repeated the following shift. Referred to the tooling backlog; no model impact.

### Review entry 1325 — efficiency bench
Rao on shift. Ambient magnetic shielding was re-measured after building works. Values remained inside the acceptance envelope for the transport bench. Closed with no action required.

### Review entry 1332 — probe bench
Nadia on shift. The shift rota changed to accommodate the recertification window. No bench parameters were touched during the transition. No estimator semantics changed in this entry.

### Review entry 0047 — conditioning bench
> **Calibration decision (2026-05-25 - MX-2251)** Nadia: duplicate-link collapse is REVERSED. Repeated directed links in the network export come from the acquisition path re-reporting a channel after a probe reset, and the re-report carries the optimistic reading rather than the settled one. Where a directed link (source, target) appears more than once, the surviving weight is the MINIMUM of the reported weights, not the maximum. The self-loop rejection and the 1..9 validity bound recorded in MX-2201 are unchanged; only the duplicate comparison reverses. This supersedes the maximum-collapse rule in MX-2201.

### Review entry 0049 — conditioning bench
> **Calibration decision (2026-05-25 - MX-2253)** Nadia: duplicate-site damping collapse is REVERSED for the same reason. Where a site appears more than once in the conditioning file, the surviving damping is the MINIMUM of the in-range values, not the maximum. Out-of-range values are still DISCARDED rather than clamped, and sites absent from the file still damp by 0. This supersedes the maximum-collapse rule in MX-2215.

> **Calibration decision (2026-05-24 - MX-2257)** Nadia: site contention (final). The routed channels are site-disjoint, but the candidate paths that were NOT routed still contend for sites the routed channels hold. A candidate that contends for sites held by more than one routed channel is attributed to exactly ONE of them, not to each. For each unrouted candidate, take the routed channels it shares at least one non-source site with (its claimants) and pick the OWNER: highest `channel_flux`, ties broken by smallest endpoint. The owner then adds to its `contention_overlap` the number of sites IT ITSELF shares with that candidate -- the size of the intersection of the owner's own non-source site set with the candidate's. Every other claimant adds zero for that candidate. The owner does NOT absorb sites the candidate shares only with some other claimant; those are counted by nobody. Worked example: unrouted candidate U covers sites {a, b}; routed channel A (channel_flux 30) covers {a}; routed channel B (channel_flux 20) covers {b}. A is the owner because its flux is higher, and A adds |{a} INTERSECT {a, b}| = 1 -- not 2. B adds 0, and site b is counted by nobody. `contention_overlap` is then subtracted from the channel flux ALONGSIDE the halved damping and BEFORE the hop attenuation: `damped_flux = max(channel_flux - ceil(damping_sum / 2) - contention_overlap, 0)`, and the contention term is NOT halved and NOT rounded -- it is a plain site count. `total_contention_overlap` sums `contention_overlap` over the routed channels, so a reader who lets every claimant count its own intersection, or who lets the owner absorb the whole contended set, will overstate it.

> **Calibration decision (2026-05-24 - MX-2259)** Ilya: dispatch retune (final). Subtracting `contention_overlap` lowers every contended channel's conditioned flux, so the admission floor and the primary threshold are retuned to sit ON the new distribution rather than above it. A routed channel is dispatched when `conditioned_flux >= 5`, revising the `>= 7` in MX-2221, and the first `primary` clause becomes `conditioned_flux >= 6` with `damping_sum <= 7`, revising the `>= 8` there. Everything else in MX-2221 stands: the clause order, the saturated-with-`hops <= 1` alternative for `primary`, the `secondary` clause, `tertiary` as the fallback, and the sorted `dispatched_endpoints`. Both thresholds now fall exactly on values that channels attain, so a one-unit slip anywhere upstream -- a damping ceil read as a floor, a contention overlap double-counted -- moves a channel across a boundary and changes the dispatched set, the class counts, the dispatch order and the dispatch checksum together.

> **Calibration decision (2026-05-26 - MX-2261)** Priya: per-hub transport policy (final). The dispatch and ledger thresholds are no longer single global constants. They are resolved PER CHANNEL from `/app/data/transport_policies.json` at that fixed absolute path, keyed by the channel's INGRESS HUB -- its first hop, `seq[1]`, not its endpoint and not any site further along the path. Resolution is three tiers, each overlaying the one before it: the shipped baseline `dispatch_floor=5, primary_min=6, primary_damping_max=7, saturation_threshold=20, throughput_cap=60`; then the file's `default` object, which may name only SOME fields -- every field it omits keeps its baseline value; then that hub's entry in `hub_overrides`, keyed by the hub number as a STRING, which is likewise sparse and inherits every field it does not name. An override is never a complete policy on its own, and a hub with no entry resolves to the file default. The five resolved fields replace the former constants exactly: `dispatch_floor` is the admission floor of MX-2259, `primary_min` and `primary_damping_max` are the first `primary` clause of MX-2221 as retuned by MX-2259, `saturation_threshold` is the ledger saturation bar and `throughput_cap` the carry cap of MX-2213. Those entries still govern everything else about their stages; only the threshold VALUES move here. `policy_checksum` is sha256 over one line per policy, joined by newline. The FIRST line is the resolved default and begins with the literal token `default` exactly as a hub line begins with its hub number -- `default|` then the five resolved values in the field order listed above, joined by `|`. It is followed by one line per overridden hub in ASCENDING NUMERIC hub order, each `hub|` then the five resolved values. Every line carries a leading token and a `|`; none is a bare value list. Note the resolved values, not the raw override values.

### Review entry 0051 — dispatch bench
> **Calibration decision (2026-05-26 - MX-2255)** Ilya: dispatch capacity cap. The dispatch list is capped at TWO channels per class. The cap is applied as a final pass over the fully ordered dispatch list, not during admission and not per class before ordering: admit, classify and order every channel as before per MX-2221 and MX-2223, then walk the ordered list from the top keeping the first two channels of each class and discarding the rest. Which channels survive therefore depends on the global ordering chain. `class_counts`, `dispatched_endpoints`, `dispatched_channel_count`, `total_conditioned_flux`, `max_conditioned_flux`, `dispatch_order` and `dispatch_checksum` all describe the dispatch list AFTER the cap.

### Review entry 0043 — conditioning bench
> **Calibration decision (2026-05-16 - MX-2215)** Nadia: site conditioning (final) — site damping is read from `/app/data/site_conditioning.json`, an object with a `sites` list of `{site, damping}` entries. This path is FIXED and absolute: `--input` selects the network only and never relocates the conditioning file. Coerce `site` and `damping` to int; DISCARD any entry whose damping falls outside the inclusive range 0..12 (do not clamp it into range); when a site is listed more than once, collapse the repeats keeping the MAXIMUM damping. A site absent from the file damps by 0. This supersedes MX-1925 and MX-2124.

### Review entry 0044 — damping bench
> **Calibration decision (2026-05-17 - MX-2217)** Nadia: channel damping (final) — a routed channel accumulates `damping_sum`, the total damping of the non-source sites it visits (the source site never contributes). Its damped flux is `damped_flux = max(channel_flux - ceil(damping_sum / 2), 0)`: the accumulated damping is halved and ROUNDED UP (ceiling), so an odd damping sum costs one more unit than a floored halving would. Written in integer arithmetic, `ceil(x / 2)` is `-(-x // 2)`. This revises the floor form in MX-2128 and supersedes MX-1928. ROUNDING: damping_sum // 2 = CEIL.

### Review entry 0045 — dispatch bench
> **Calibration decision (2026-05-18 - MX-2219)** Ilya: hop attenuation (final) — after damping, a channel is further attenuated by `(hops * 3) // 2`, integer floor division, and the result floors at zero: `conditioned_flux = max(damped_flux - (hops * 3) // 2, 0)`. Note the asymmetry with MX-2217 deliberately: the damping half rounds UP, this hop term rounds DOWN. This supersedes MX-2132.

### Review entry 0046 — dispatch bench
> **Calibration decision (2026-05-20 - MX-2221)** Ilya: dispatch admission and class — a routed channel is dispatched when `conditioned_flux >= 7`. *(Revised on this point by MX-2259 (2026-05-24), which retunes the admission floor and the primary-class threshold for the contention-adjusted conditioned flux; the class clause ORDER, the saturation and hop conditions, the secondary clause and `dispatched_endpoints` below are unchanged and still govern.)* Dispatched channels carry exactly one of THREE classes, evaluated in clause order, the first match fixing the class: `primary` when `conditioned_flux >= 8` with `damping_sum <= 7` (threshold retuned by MX-2259), or when the channel is saturated (per the MX-2213 ledger) with `hops <= 1`; otherwise `secondary` when the channel is saturated, or `damped_flux >= 12`; otherwise `tertiary`. `dispatched_endpoints` are the terminal sites of dispatched channels, sorted ascending. This supersedes MX-1931 and MX-2136.

### Review entry 0047 — dispatch bench
> **Calibration decision (2026-05-21 - MX-2223)** Marta: dispatch reporting (final) — `class_counts` always enumerates ALL THREE class names in the order `primary`, `secondary`, `tertiary`, emitting 0 for a class with no dispatched channels. `dispatch_order` lists the terminal sites of the dispatched channels ordered strictly in this sequence: class rank `primary` > `secondary` > `tertiary`; then `conditioned_flux` descending; then `damped_flux` descending; then `channel_flux` descending; then `throughput` descending; then `hops` ascending; then terminal site ascending. `total_conditioned_flux` sums `conditioned_flux` over the dispatched channels and `max_conditioned_flux` is the largest (0 when none are dispatched); `total_damping` sums `damping_sum` over ALL routed channels, dispatched or not. This supersedes MX-2140.

### Review entry 0041 — audit bench
Bench run logged nominal transport; quarterly recertification touched this lane, no estimator-relevant configuration changed.

### Review entry 0042 — audit bench
> **Calibration decision (2026-05-24 - MX-2240)** Priya: calibration dashboards retain ninety days of run history; older runs are served from the archive on demand. Dashboard retention is an operational setting and carries no weight in the estimator output.
