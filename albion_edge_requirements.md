# AlbionEdge — Project Requirements & Overview

**Author:** Pete
**Type:** Portfolio project (data science, statistics, ML, full-stack engineering)
**Target timeline:** 8 weekends, starting after semester finals
**Total cost:** $0 (all free-tier infrastructure)

---

## 1. Project Overview

AlbionEdge is a market intelligence platform for *Albion Online*, a sandbox MMO with a fully player-driven economy. Existing tools (Albion Free Market, Tools4Albion, AlbionOnline2D) show current price snapshots — what an item costs *right now*. AlbionEdge answers statistical questions that no existing tool addresses:

- *Is this price anomalously low compared to its historical distribution?*
- *What is the probability this item's price rises in the next 24 hours, with a calibrated confidence interval?*
- *Is the cross-city spread on this item statistically wider than usual, accounting for normal volatility?*
- *Which Black Market flips are profitable at a statistically significant level after accounting for transport risk?*

**Target users:** Economy-focused Albion players — crafters, flippers, Black Market traders, and transporters — who currently rely on spreadsheets and intuition.

**Why this dataset is rich for a portfolio project:**
- *Spatial arbitrage* across 6+ cities (Caerleon, Bridgewatch, Lymhurst, Fort Sterling, Martlock, Thetford, Brecilien) creates a natural commodity-arbitrage modeling problem.
- *The Black Market* — NPCs that buy player-crafted gear at algorithmically set prices — is a real, high-demand use case.
- *Crafting cost chains* (raw → refined → crafted) allow full supply-chain modeling.
- *Gold-to-Silver exchange rate* behaves like a forex pair with its own time series dynamics.

---

## 2. Data Sources

### Primary: Albion Online Data Project (AODP) API

- **Base URL:** `https://west.albion-online-data.com/api/v2/stats/`
- **No API key required** — fully public REST API
- **Endpoints used:**
  - `prices/{item_ids}` — current buy/sell orders by city
  - `history/{item_ids}?time-scale=1` — hourly historical averages
  - `history/{item_ids}?time-scale=24` — daily historical averages
  - `charts/{item_ids}` — chart-formatted historical data
  - `gold` — gold-to-silver exchange rate history
- **Parameters:** `locations`, `qualities`, `date`, `end_date`, `time-scale`
- **Item ID format:** `T{tier}_{ITEM}@{enchantment}`, e.g. `T4_BAG`, `T6_PLANKS@2`
- **Location IDs:** `Caerleon`, `Bridgewatch`, `Fort Sterling`, `Lymhurst`, `Martlock`, `Thetford`, `Brecilien`, `Black Market`
- **Rate limits:** No hard published limit — be respectful: gzip encoding, batched requests, aggressive caching.

### Supplementary (static / manual)

- **Patch/update dates** — manually logged from Albion Online forum announcements (used for changepoint analysis).
- **City crafting bonuses** — static game data, rarely changes.
- **Item metadata** — `items.json` from AODP (tier, category, enchantment, crafting recipe).

---

## 3. Functional Requirements

### 3.1 Data pipeline
- Pull current prices and historical data daily for a curated set of ~100–200 tracked items (resources T4–T8, popular weapons/armor, crafting mats).
- Store all observations in PostgreSQL with idempotent UPSERTs (re-running the pipeline must not create duplicates).
- Validate incoming data: no nulls in required fields, no negative prices, flag timestamp gaps.
- Log API failures with retry logic; surface persistent failures.

### 3.2 Statistical inference layer
- Fit GLMs for price and volume: Gamma regression for price levels (positive, right-skewed), Poisson/negative binomial for trade volume counts.
- Test for city effects: do prices in Caerleon systematically differ from Bridgewatch after controlling for tier? Use LRTs comparing nested models.
- Changepoint detection around known patch dates.
- Bootstrap confidence intervals on inter-city price spreads.
- Stationarity tests (ADF, KPSS) on spread time series to identify mean-reverting arbitrage opportunities.
- Anomaly scoring: flag observations in the tails of the fitted conditional distribution.

### 3.3 ML prediction layer
- Feature engineering: lagged returns, rolling volatility, volume ratios, spread vs. historical mean, days since last patch, gold price momentum.
- Walk-forward cross-validation (no temporal leakage).
- Baseline: logistic regression for price-direction classification.
- Challenger: gradient-boosted trees (XGBoost or LightGBM) for direction and magnitude.
- Model comparison with proper calibration plots, Brier scores, and honest confidence intervals on accuracy.
- **Explicit acceptance of null findings:** if models can't beat a random-walk baseline, that is a legitimate, documented result.

### 3.4 API
FastAPI backend exposing:
```
GET  /api/items                       # list tracked items
GET  /api/items/{item_id}/prices      # price history, optional filters
GET  /api/items/{item_id}/stats       # stat summary (CI, volatility, anomaly score)
GET  /api/items/{item_id}/predict     # ML prediction with confidence
GET  /api/signals                     # current anomalies and strong predictions
GET  /api/arbitrage                   # cross-city opportunities with significance
GET  /api/gold                        # gold price history and trend
```

### 3.5 Frontend
React + TypeScript single-page app with:
- **Item explorer** — search/filter items → price history chart with CI bands (Recharts or Plotly).
- **Signals dashboard** — sortable table of current anomalies and predictions ranked by confidence.
- **Arbitrage scanner** — cross-city price comparison with profit estimates and statistical significance flags.
- **Methodology page** — renders the statistical and ML methodology from Markdown so recruiters can see the reasoning.

---

## 4. Non-Functional Requirements

- **Correctness over cleverness.** Every statistical claim has a derivation or citation; every CI has a stated method.
- **Reproducibility.** `docker-compose up` reproduces local dev. Seed data snapshot committed to repo for offline testing.
- **Type safety.** Python uses type hints throughout; Pydantic validates all API request/response schemas.
- **Testing.** Unit tests for data transformations and model predictions (pytest); integration tests for API endpoints.
- **CI.** GitHub Actions runs lint (ruff) + tests on every PR.
- **Observability.** Structured logging; pipeline runs emit success/failure status. No alerting system required for v1.
- **Documentation.** Clean README with architecture diagram, setup instructions, screenshots, and a methodology section linking to the write-up.

---

## 5. Architecture & Deployment Stack

| Component        | Platform               | Cost         |
|------------------|------------------------|--------------|
| Frontend (React) | Vercel                 | Free (Hobby) |
| Backend (FastAPI)| Railway **or** Render  | Free tier    |
| Database (Postgres) | Supabase            | Free (500 MB)|
| Scheduled jobs   | GitHub Actions cron    | Free         |
| CI/CD            | GitHub Actions         | Free         |

**Render vs. Railway tradeoff:** Render has a true free tier but spins down after 15 minutes of inactivity (cold start ~30s). Railway's Hobby plan ($5/mo with $5 credit) avoids cold starts and is better for a portfolio piece a recruiter might load on-demand. Decision deferred to deployment weekend — Render acceptable if cold start is called out in README.

---

## 6. Database Schema (initial)

```sql
CREATE TABLE items (
    item_id      TEXT PRIMARY KEY,          -- e.g. 'T6_PLANKS@2'
    name         TEXT NOT NULL,             -- e.g. 'Uncommon Pine Planks'
    tier         INTEGER NOT NULL,          -- 4-8
    enchantment  INTEGER DEFAULT 0,         -- 0-4
    category     TEXT,                      -- 'resource', 'armor', 'weapon', ...
    subcategory  TEXT                       -- 'plate_armor', 'wood', ...
);

CREATE TABLE price_history (
    item_id      TEXT REFERENCES items(item_id),
    city         TEXT NOT NULL,
    quality      INTEGER NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    avg_price    NUMERIC,
    item_count   INTEGER,
    PRIMARY KEY (item_id, city, quality, timestamp)
);

CREATE TABLE gold_history (
    timestamp    TIMESTAMPTZ PRIMARY KEY,
    price        NUMERIC NOT NULL
);

CREATE TABLE game_events (
    event_date   DATE PRIMARY KEY,
    event_type   TEXT NOT NULL,             -- 'patch', 'balance_update', 'season_start'
    description  TEXT
);
```

---

## 7. Timeline (8 weekends after finals)

| Weekend | Focus | Deliverable |
|---------|-------|-------------|
| 1 | Repo scaffold, DB schema, AODP API client | Working ingestion for 10 items |
| 2 | Full pipeline + GitHub Actions daily cron | Daily data flowing into Supabase |
| 3 | GLM fitting, city-effect tests, diagnostics | Stats notebook w/ LRTs and plots |
| 4 | Changepoint detection, spread CIs, stationarity | Methodology write-up draft |
| 5 | Feature engineering, baseline logistic model | Walk-forward CV harness |
| 6 | XGBoost, calibration, model comparison | Prediction endpoint spec |
| 7 | FastAPI backend, Pydantic schemas, tests | Deployed API on Railway/Render |
| 8 | React frontend, charts, dashboards, polish | Live site + README + screenshots |

**Pre-finals head start:** Spend ~30 minutes before finals setting up the GitHub Actions cron job and the DB schema so daily data is accumulating while studying. By weekend 3, weeks of history are available.

---

## 8. Out of Scope for v1

- User authentication / saved watchlists.
- Mobile-native app.
- Real-time push (WebSocket) updates — polling is fine.
- Discord bot integration.
- Crafting profitability calculator with focus cost and return rates.
- Gold price forecasting (ARIMA / Prophet).
- Black Market demand prediction.

These are documented as stretch goals and can be added post-v1 if time permits.

---

## 9. Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AODP API changes or goes down | Cache raw responses locally; document data source; project still demonstrates skills with snapshot |
| Models don't beat random walk | Treat as legitimate finding; write up rigorously with baselines and calibration |
| Free-tier DB hits 500 MB cap | Aggregate older data to daily resolution; prune quality dimensions not actively modeled |
| Render cold starts hurt demo | Document clearly in README; switch to Railway if it becomes a blocker |
| Scope creep from stretch goals | Strict v1 scope; stretch list lives in a separate doc |

---

## 10. Success Criteria

- Live, publicly accessible web app with working statistical and ML endpoints.
- GitHub repo with clean code, passing CI, and a README that explains architecture and methodology.
- Methodology write-up showing statistical reasoning (GLMs, LRTs, CIs, calibration) at a level appropriate for a quant/ML-adjacent interview.
- At least one substantive finding — whether "cross-city spreads on T6 planks are statistically wider than on T4 planks" or "price direction is not meaningfully predictable at 24h horizon" — documented with evidence.
