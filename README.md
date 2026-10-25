# Medium Access Control Mechanisms in Wi-Fi Networks

An event-driven, slotted-time simulator of IEEE 802.11 CSMA/CA (DCF), with and without RTS/CTS, for two-station and dense networks, plus a simplified Wi-Fi 6 uplink OFDMA model (extra credit). The project compares distributed contention with coordinated multi-user access.

---

## Table of contents

1. [Project overview](#project-overview)
2. [Team roles and file ownership](#team-roles-and-file-ownership)
3. [Workflow by week](#workflow-by-week)
4. [Repository structure](#repository-structure)
5. [Setup](#setup)
6. [Results](#results)

---

## Project overview

| Part | Topic | Status |
|------|-------|--------|
| I | Two-station CSMA/CA: single collision domain and hidden terminals, with and without RTS/CTS | Not started |
| II | Dense DCF networks, N in {2, 5, 10, 20, 40}, aggregate load in {300, 800} frames/sec | Not started |
| III | Simplified uplink OFDMA, K in {1, 2, 4, 8} RUs, round-robin scheduling (extra credit) | Not started |

**Metrics reported:** per-station and aggregate throughput (Mbps), collision probability, mean and 95th-percentile packet delay, Jain's Fairness Index.

---

## Team roles and file ownership

Person 1 (station MAC logic and the DCF-vs-OFDMA comparison). Person 2 (channel model, metrics, OFDMA, experiments, verification).

The work is split so each person's code can be built and tested on its own: P1 tests the station logic against a stub channel (every station hears every other), and P2 tests the channel with scripted transmissions. Neither blocks the other until integration around Day 5.

| File | Owner | Notes |
|------|-------|-------|
| `src/simulator.py` | P1 | Event queue, main loop, event types |
| `src/dcf.py` | P1 | Backoff selection, freeze/resume, DIFS/SIFS/ACK sequencing, binary exponential backoff, RTS/CTS frame sequence |
| `src/channel.py` | P2 | Sensing matrix (hidden terminals), overlap and collision detection, busy/idle notifications, NAV |
| `src/station.py` | Both (Day 1) | Shared interface. Changes after Day 1 need both people to agree |
| `src/config.py` | Both (Day 1) | Simulation parameters from Table 1 of the assignment, plus any added (e.g. OFDMA overhead) |
| `src/metrics.py` | P2 | Throughput, collision probability, delay, Jain's index |
| `src/ofdma.py` | P2 | Round-robin scheduler, K RUs, overhead model |
| `experiments/part1.py` | P2 | Two-station sweeps and Part I figures |
| `experiments/part2.py` | P2 | Dense sweeps and Part II figures |
| `experiments/part3.py` | P1 | DCF vs. OFDMA comparison and figures 7-9 |
| `tests/test_deterministic.py` | Both | P1 writes the DCF timeline cases (stub channel), P2 writes the channel cases (scripted transmissions) |
| `results/`, `figures/` | P2 | Generated output, never edited by hand |
| `requirements.txt`, `README.md` | P2 | Kept up to date alongside experiments |

**Report split** (the report is written separately from this repo)

- **P1:** Simulator design; Part I analysis; OFDMA analysis
- **P2:** Verification; Results; Part II analysis
- **Both:** Introduction (with team responsibilities), Conclusion, AI-use statement


---

## Workflow by week

---

### Week 1: Build and verify the simulator (Days 1-7)

**Goal:** a working, tested simulator and complete Part I results.

#### Days 1-2: Setup and interfaces

- [x] **Both:** Create the repo, add this README, `requirements.txt`, `.gitignore`, and the folder layout.
- [x] **Both:** Agree on the interfaces: station fields, event types, the results dictionary returned by a run, and the channel API (how a station starts a transmission, asks whether the channel is busy, is notified of busy/idle changes, and learns the outcome).
- [x] **Both:** Decide the time unit (integer slot counts) and random-seed handling.
- [x] **P2:** Write `station.py`, `config.py`, and Poisson arrival generation.

#### Days 2-4: Station logic and channel, built independently

- [x] **P1:** Implement the event queue (`heapq`) and event types: arrival, backoff expiry, transmission start/end, ACK.
- [x] **P1:** Implement backoff selection, DIFS sensing, freeze/resume, and ACK after SIFS.
- [x] **P1:** Implement collision handling and binary exponential backoff, tested against a stub channel (single collision domain).
- [x] **P1:** Write the first deterministic test case with a hand-built event timeline.
- [x] **P2:** Implement `channel.py`: busy/idle tracking, overlap and collision detection, and NAV, tested with scripted transmissions.
- [x] **P2:** Write `metrics.py` against a stub result so it is ready when the engine is.
- [ ] **Milestone (Day 4):** single-collision-domain DCF matches the first hand-built timeline. If not, fix this before moving on.

#### Days 5-7: Integration, hidden terminals, RTS/CTS, and Part I results

> The most likely time sink. Budget extra time here.

- [ ] **Both:** Integrate P1's station logic with P2's channel (budget half a day for bugs at the join).
- [ ] **P2:** Add the sensing matrix so A and B cannot sense each other but both reach the AP, with partial-overlap collisions at the AP.
- [ ] **P1:** Implement the RTS/CTS frame sequence, including RTS collisions and backoff, using P2's NAV handling.
- [ ] **P2:** Write the channel test cases (hidden terminals, NAV) as deterministic tests.
- [ ] **P2:** Build `part1.py`: 6 values of λ x 2 topologies x with/without RTS/CTS x multiple seeds.
- [ ] **P2:** Generate the Part I figures (throughput of A and B vs. λ; collision probability vs. λ).
- [ ] **P1:** Start drafting the Simulator design section of the report.
- [ ] **Milestone (Day 7):** Part I results and figures complete.

---

### Week 2: Dense networks, OFDMA, and the report (Days 8-14)

**Goal:** all required figures, the extra credit if time allows, and a finished report.

#### Days 8-10: Dense networks (Part II)

- [ ] **Both:** Confirm the engine runs for any N in a single collision domain.
- [ ] **P2:** Build `part2.py`: N in {2, 5, 10, 20, 40} x Λ in {300, 800} x multiple seeds, with per-station λᵢ = Λ/N.
- [ ] **P2:** Add mean and 95th-percentile delay and Jain's Fairness Index to the output.
- [ ] **P2:** Generate the four Part II figures (throughput, collision probability, delay, fairness vs. N).
- [ ] **Both:** Run the full sweep in parallel with `multiprocessing`, starting early so it finishes in time.
- [ ] **P1:** Write the Part I analysis (collisions, RTS/CTS, hidden terminals).
- [ ] **Milestone (Day 10):** all required figures (1-6) generated.

#### Days 10-12: OFDMA extra credit (Part III)

> Flex phase. If Parts I and II are not solid by Day 10, skip this and polish the required work.

- [ ] **P2:** Implement the round-robin scheduler in `ofdma.py` with K RUs and a rate of 12/K Mbps per RU.
- [ ] **P2:** Choose and document a fixed scheduling overhead per OFDMA opportunity and apply it consistently.
- [ ] **P1:** Build `part3.py`: DCF vs. OFDMA (K = 1, 2, 4, 8) at N = 20 over a range of Λ, and generate figures 7-9.
- [ ] **P1:** Write the OFDMA analysis.
- [ ] **P2:** Write the Part II analysis and the Verification section.

#### Days 11-14: Report writing and final checks

- [ ] **P2:** Write the Results section with labeled, captioned figures.
- [ ] **Each person:** Write the analysis for the parts they own, explaining *why* each curve behaves as it does (contention, backoff, queue buildup, retransmissions, saturation), not just what it does.
- [ ] **Both:** Answer all numbered questions from the assignment using evidence from the results.
- [ ] **Both:** Write the Introduction, Conclusion, and AI-use statement.
- [ ] **Both:** Cross-read the whole report and check page limits: Introduction (1 page), Simulator design (1 page), Verification (1 page), Analysis (about 4-5 pages), Conclusion (half a page).
- [ ] **Both:** Final check: consistent axes, markers, and line styles; units and legends present; code runs from a clean clone.

---

## Repository structure

> Update this section if the layout changes.

```
wifi-medium-access-control/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── config.py           # simulation parameters
│   ├── simulator.py        # event queue and main simulation loop
│   ├── station.py          # per-station state
│   ├── dcf.py              # station MAC logic: backoff, RTS/CTS sequence
│   ├── channel.py          # sensing matrix, collisions, busy/idle, NAV
│   ├── ofdma.py            # round-robin OFDMA scheduler
│   └── metrics.py          # throughput, collisions, delay, Jain's index
├── experiments/
│   ├── part1.py            # two-station sweeps
│   ├── part2.py            # dense-network sweeps
│   └── part3.py            # DCF vs. OFDMA comparison
├── tests/
│   └── test_deterministic.py   # hand-built timeline verification cases
├── results/                # generated data (CSV/JSON)
└── figures/                # generated plots
```

---

## Setup

Requires Python 3.9 or newer.

```bash
git clone <repo-url>
cd wifi-medium-access-control
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Results

Figures are generated into `figures/` and discussed in the report:

1. Part I throughput vs. λ (both topologies, with and without RTS/CTS)
2. Part I collision probability vs. λ
3. Dense DCF aggregate throughput vs. N
4. Dense DCF collision probability vs. N
5. Dense DCF mean and 95th-percentile delay vs. N
6. Dense DCF Jain's Fairness Index vs. N
7. DCF vs. OFDMA throughput, N = 20 (extra credit)
8. DCF vs. OFDMA 95th-percentile delay, N = 20 (extra credit)
9. DCF vs. OFDMA fairness, N = 20 (extra credit)
