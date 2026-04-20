# AlbionEdge — Market Intelligence Platform

## Project Spec & Implementation Plan

**Author:** Pete
**Timeline:** 8 weekends (~6–8 hrs each), starting after finals
**Goal:** Showcase data science, statistical inference, ML, and software engineering skills in a single, deployed, real-impact project.

---

## 1. Overview

AlbionEdge is an end-to-end market intelligence platform for Albion Online's player-driven economy. It ingests historical and live price data from the Albion Online Data Project (AODP) API, runs statistical models and ML predictions, and serves results through a polished React web app.

**What makes this different from existing tools:**
Existing tools (Albion Free Market, Tools4Albion, AlbionOnline2D) show current snapshots — what's the price *right now*. AlbionEdge answers statistical questions: *Is this price anomalously low? What's the probability this item's price rises in the next 24 hours? Is the cross-city spread statistically wider than usual?* No existing tool does this.

**Target users:** Economy-focused Albion players (crafters, flippers, Black Market traders, transporters) who currently rely on spreadsheets and gut feel.

---

## 2. Data Sources

### Primary: Albion Online Data Project (AODP) API
- **Base URL:** `https://west.albion-online-data.com/api/v2/stats/`
- **No API key required** — fully public REST API
- **Endpoints:**
  - `prices/{item_ids}` — current buy/sell orders by city
  - `history/{item_ids}?time-scale=1` — hourly historical averages
  - `history/{item_ids}?time-scale=24` — daily historical averages
  - `charts/{item_ids}` — chart-formatted historical data
- **Parameters:** `locations`, `qualities`, `date`, `end_date`, `time-scale`
- **Item IDs:** Tier + enchantment format, e.g., `T4_BAG`, `T6_PLANKS@2` (tier 6, enchantment 2)
- **Location IDs:** `Caerleon`, `Bridgewatch`, `Fort Sterling`, `Lymhurst`, `Martlock`, `Thetford`, `Brecilien`, `Black Market`
- **Rate limits:** Be respectful — use gzip, batch requests, cache aggressively

### Secondary: Gold Price History
- `https://west.albion-online-data.com/api/v2/stats/gold`
- Gold-to-silver exchange rate over time (acts like a forex pair)

### Supplementary (manual)
- Patch/update dates (from Albion Online forum announcements)
- City crafting bonuses (static game data, changes rarely)
- Item metadata: `items.json` from AODP (tier, category, enchantment, crafting recipe)

---

## 3. Database Schema

**Platform:** Supabase (free-tier PostgreSQL) or local SQLite for development.

```sql
-- Core item metadata
CREATE TABLE items (
    item_id TEXT PRIMARY KEY,          -- e.g., 'T6_PLANKS@2'
    name TEXT NOT NULL,                -- e.g., 'Uncommon Pine Planks'
    tier INTEGER NOT NULL,             -- 4-8
    enchantment INTEGER DEFAULT 0,     -- 0-4
    category TEXT,                     -- 'resource', 'armor', 'weapon', 'consumable', etc.
    subcategory TEXT,                  -- 'plate_armor', 'sword', 'wood', etc.
    crafting_inputs JSONB              -- recipe: [{item_id, quantity}]
);

-- Daily price history (primary analysis table)
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    item_id TEXT REFERENCES items(item_id),
    location TEXT NOT NULL,            -- city name
    quality INTEGER DEFAULT 1,         -- 1-5
    timestamp TIMESTAMPTZ NOT NULL,
    avg_price NUMERIC,
    item_count INTEGER,                -- volume
    UNIQUE(item_id, location, quality, timestamp)
);

-- Current order book snapshots
CREATE TABLE order_snapshots (
    id SERIAL PRIMARY KEY,
    item_id TEXT REFERENCES items(item_id),
    location TEXT NOT NULL,
    quality INTEGER DEFAULT 1,
    sell_price_min INTEGER,
    sell_price_max INTEGER,
    buy_price_min INTEGER,
    buy_price_max INTEGER,
    sell_order_count INTEGER,
    buy_order_count INTEGER,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Gold-silver exchange rate
CREATE TABLE gold_history (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    price INTEGER NOT NULL,            -- silver per gold
    UNIQUE(timestamp)
);

-- Game events (patches, updates) — manually maintained
CREATE TABLE game_events (
    id SERIAL PRIMARY KEY,
    event_date DATE NOT NULL,
    event_type TEXT,                   -- 'major_patch', 'balance_update', 'season_start'
    description TEXT,
    source_url TEXT
);

-- Model predictions (written by ML pipeline)
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    item_id TEXT REFERENCES items(item_id),
    location TEXT NOT NULL,
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    horizon_hours INTEGER,             -- prediction window (e.g., 24, 168)
    direction TEXT,                    -- 'up', 'down', 'stable'
    probability NUMERIC,              -- model confidence
    model_version TEXT
);

-- Detected anomalies
CREATE TABLE anomalies (
    id SERIAL PRIMARY KEY,
    item_id TEXT REFERENCES items(item_id),
    location TEXT NOT NULL,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    anomaly_type TEXT,                 -- 'price_spike', 'volume_surge', 'spread_widening'
    severity NUMERIC,                 -- z-score or similar
    description TEXT
);
```

---

## 4. Item Universe

Start focused, expand later. Priority items (~150-200 total):

| Category | Examples | Why |
|----------|----------|-----|
| Raw resources (T4-T8) | Ore, Hide, Fiber, Wood, Stone | High volume, clear supply/demand dynamics |
| Refined resources (T4-T8) | Bars, Leather, Cloth, Planks, Blocks | Crafting chain analysis |
| Popular weapons | Claymore, Greataxe, Bows, Staffs | Black Market demand |
| Popular armor | Plate, Leather, Cloth sets | Black Market demand |
| Consumables | Potions, food, mounts | Driven by PvP/GvG activity |
| Enchanted variants (@1-@3) | Key resources at each enchantment level | Price dynamics differ by enchantment |

---

## 5. Skill Pillars — What Each Component Demonstrates

### 5A. Statistical Inference (weeks 3–4)

**Models:**
- **Gamma GLM for price levels.** Prices are positive and right-skewed — Gamma with log link is the natural choice. Predictors: tier, enchantment, city, day-of-week, days-since-patch.
- **Poisson/Negative Binomial GLM for trade volume.** Volume is count data. Test for overdispersion; if present, use NB. Predictors: same as above plus price deviation from 7-day MA.
- **Zero-inflated model** if relevant (some item-city pairs have zero-volume days).

**Hypothesis tests:**
- LRT: Does adding `city` as a predictor significantly improve the price model? (nested model comparison — you know the λ_LR = sup H₀ / sup unrestricted convention)
- Test whether patch dates cause structural breaks (Chow test or changepoint detection via `ruptures` package)
- Test for day-of-week effects on volume (are weekends higher volume?)
- Test whether inter-city price spreads are stationary (ADF test) — if so, mean-reversion arbitrage is statistically grounded

**Confidence intervals:**
- CIs on rolling 7-day returns
- CIs on cross-city price ratios
- Bootstrap CIs on arbitrage profitability (buy in city A, sell in city B — what's the distribution of profit after accounting for transport risk?)

**Deliverable:** A methodology page on the site explaining the statistical approach, with proper notation and interpretation. This is what separates the project from a typical Kaggle notebook.

### 5B. Machine Learning (weeks 5–6)

**Task:** Binary classification — will an item's price in a given city increase or decrease over the next 24 hours (or 7 days)?

**Features (all constructed without future leakage):**
- Lagged returns: 1-day, 3-day, 7-day price change
- Rolling volatility: 7-day and 30-day standard deviation of returns
- Volume ratios: current volume / 7-day average volume
- Spread features: current price vs. 30-day MA (mean reversion signal)
- Cross-city features: price in this city vs. median price across all cities
- Gold price momentum: 7-day gold price change
- Calendar features: day of week, days since last major patch
- Crafting margin: current sell price vs. estimated crafting cost (for craftable items)

**Models:**
1. **Logistic regression baseline** (statsmodels) — interpretable, connects to inference layer
2. **XGBoost / LightGBM** — performance model
3. Compare via walk-forward cross-validation (train on months 1-3, test on month 4; train on months 1-4, test on month 5; etc.)

**Evaluation:**
- Precision/recall curves (not just accuracy — class balance matters)
- Calibration plots (is a predicted 70% probability actually 70%?)
- Feature importance (SHAP values for XGBoost)
- Compare against naive baselines (always predict "up", random walk)

**Anti-leakage checklist:**
- [ ] No features use future price data
- [ ] No features use same-day data for same-day prediction
- [ ] Walk-forward split respects temporal ordering
- [ ] No item-level information leakage across train/test

### 5C. Data Engineering (weeks 1–2)

- **ETL pipeline:** Python scripts that hit the AODP API, transform responses, and load into Postgres
- **Scheduled ingestion:** GitHub Actions cron job runs daily, pulls latest prices for all tracked items
- **Idempotent loads:** UPSERT logic so re-running doesn't create duplicates
- **Error handling:** Retry logic for API failures, logging, alerting (even if just logging to a file)
- **Data validation:** Check for nulls, negative prices, timestamp gaps

### 5D. Software Engineering (weeks 7–8)

**Backend — FastAPI (Python):**
```
GET  /api/items                         # list tracked items
GET  /api/items/{item_id}/prices        # price history with optional filters
GET  /api/items/{item_id}/stats         # statistical summary (CI, volatility, anomaly score)
GET  /api/items/{item_id}/predict       # ML prediction with confidence
GET  /api/signals                       # current anomalies and strong predictions
GET  /api/arbitrage                     # cross-city opportunities with statistical significance
GET  /api/gold                          # gold price history and trend
```

**Frontend — React + TypeScript:**
- **Item explorer:** Search/filter items → price history chart with CI bands (Recharts or Plotly)
- **Signals dashboard:** Table of current anomalies and predictions, sortable by confidence
- **Arbitrage scanner:** Cross-city price comparison with profit estimates and statistical significance
- **Methodology page:** Explains the stats/ML approach (renders from Markdown)

**Engineering practices:**
- Type hints throughout Python code
- Pydantic models for API request/response validation
- Unit tests for data transformations and model predictions (pytest)
- Integration tests for API endpoints
- GitHub Actions CI: lint (ruff) + test on every PR
- Docker-compose for local development
- Clean README with architecture diagram, setup instructions, screenshots

---

## 6. Deployment (Free Tier)

| Component | Platform | Cost |
|-----------|----------|------|
| Frontend (React) | Vercel | Free |
| Backend (FastAPI) | Render | Free tier (spins down after inactivity) |
| Database (Postgres) | Supabase | Free tier (500 MB, sufficient) |
| Scheduled jobs | GitHub Actions | Free (2,000 min/month) |
| CI/CD | GitHub Actions | Same free tier |

**Cold start note:** Render free tier sleeps after 15 min of inactivity. First request takes ~30s. This is fine for a portfolio project — mention it in the README. If you want always-on later, Railway offers a free trial.

---

## 7. Week-by-Week Plan

### Weekend 1 — Project Setup & API Exploration
- [ ] Create GitHub repo with proper structure (see §8)
- [ ] Write Python script to hit AODP API, explore response format
- [ ] Download `items.json` metadata, parse into a lookup table
- [ ] Pick initial item universe (~150 items)
- [ ] Set up local SQLite for rapid prototyping
- [ ] Write first EDA notebook: pull 30 days of history for 10 items, plot prices

### Weekend 2 — ETL Pipeline & Data Accumulation
- [ ] Design and create Postgres schema on Supabase
- [ ] Build ETL pipeline: fetch → transform → load with UPSERT
- [ ] Add error handling, retry logic, logging
- [ ] Set up GitHub Actions cron job (daily pull)
- [ ] Validate: spot-check prices against in-game or AFM
- [ ] Begin accumulating daily data (runs every day from here on)

### Weekend 3 — EDA & Initial Statistical Analysis
- [ ] EDA notebook: distributions, volatility, autocorrelation, cross-city correlations
- [ ] Identify which items have sufficient data for modeling
- [ ] Fit Gamma GLM for price levels (statsmodels)
- [ ] Test for city effects (LRT)
- [ ] Visualize residuals, check model diagnostics

### Weekend 4 — Statistical Inference Deep Dive
- [ ] Changepoint detection around patch dates (ruptures)
- [ ] Poisson/NB GLM for volume, test for overdispersion
- [ ] Bootstrap CIs on inter-city arbitrage returns
- [ ] ADF tests on price spreads (stationarity → mean reversion)
- [ ] Day-of-week effect tests
- [ ] Draft methodology write-up

### Weekend 5 — Feature Engineering & ML Baseline
- [ ] Build feature engineering pipeline (all features in §5B)
- [ ] Implement walk-forward cross-validation splitter
- [ ] Train logistic regression baseline
- [ ] Evaluate: precision/recall, calibration, vs. naive baselines
- [ ] Audit for data leakage

### Weekend 6 — ML Performance Model & Comparison
- [ ] Train XGBoost/LightGBM
- [ ] Hyperparameter tuning (Optuna or grid search)
- [ ] SHAP feature importance analysis
- [ ] Compare all models (logistic, XGBoost, naive) in a summary table
- [ ] Serialize best model for serving (joblib)
- [ ] Write prediction serving logic

### Weekend 7 — Backend API & Frontend
- [ ] Build FastAPI app with all endpoints (§5D)
- [ ] Add Pydantic models, input validation
- [ ] Scaffold React app (Vite + TypeScript)
- [ ] Build item explorer page with price chart + CI bands
- [ ] Build signals dashboard
- [ ] Build arbitrage scanner page

### Weekend 8 — Polish, Deploy, Launch
- [ ] Deploy frontend to Vercel
- [ ] Deploy backend to Render
- [ ] Connect to Supabase production DB
- [ ] Write unit tests + integration tests
- [ ] Set up GitHub Actions CI (lint + test)
- [ ] Polish README: architecture diagram, screenshots, methodology link
- [ ] Write methodology page for the site
- [ ] (Optional) Post to r/albiononline or Albion Discord for real user feedback

---

## 8. Repo Structure

```
albion-edge/
├── README.md
├── .github/
│   └── workflows/
│       ├── ci.yml              # lint + test on PR
│       └── daily_ingest.yml    # scheduled data pull
├── data/
│   ├── items.json              # item metadata
│   └── game_events.csv         # manually maintained patch dates
├── pipeline/
│   ├── __init__.py
│   ├── config.py               # API URLs, item universe, DB connection
│   ├── fetch.py                # AODP API client
│   ├── transform.py            # data cleaning, validation
│   ├── load.py                 # DB UPSERT logic
│   └── run_pipeline.py         # orchestrator (called by cron)
├── analysis/
│   ├── notebooks/
│   │   ├── 01_eda.ipynb
│   │   ├── 02_glm_price.ipynb
│   │   ├── 03_volume_model.ipynb
│   │   ├── 04_changepoints.ipynb
│   │   └── 05_ml_pipeline.ipynb
│   ├── inference/
│   │   ├── glm.py              # Gamma GLM, Poisson GLM fitting
│   │   ├── changepoint.py      # ruptures-based detection
│   │   ├── arbitrage.py        # cross-city spread analysis
│   │   └── tests.py            # hypothesis tests (LRT, ADF, etc.)
│   └── ml/
│       ├── features.py         # feature engineering
│       ├── train.py            # model training + walk-forward CV
│       ├── evaluate.py         # metrics, calibration, SHAP
│       └── predict.py          # load model, serve predictions
├── backend/
│   ├── main.py                 # FastAPI app
│   ├── routers/
│   │   ├── items.py
│   │   ├── signals.py
│   │   ├── arbitrage.py
│   │   └── gold.py
│   ├── models.py               # Pydantic schemas
│   ├── database.py             # DB connection, queries
│   └── tests/
│       ├── test_items.py
│       └── test_signals.py
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── ItemExplorer.tsx
│   │   │   ├── Signals.tsx
│   │   │   ├── Arbitrage.tsx
│   │   │   └── Methodology.tsx
│   │   ├── components/
│   │   │   ├── PriceChart.tsx
│   │   │   ├── SignalTable.tsx
│   │   │   └── ItemSearch.tsx
│   │   └── api/
│   │       └── client.ts       # API client (axios/fetch wrapper)
│   └── public/
├── docker-compose.yml          # local dev: postgres + backend + frontend
├── requirements.txt
└── pyproject.toml
```

---

## 9. Key Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| AODP API goes down or changes | No new data | Cache aggressively; design pipeline to handle gaps; keep local backups |
| Insufficient historical data | Weak models | Start data accumulation ASAP (weekend 2); supplement with wider time-scale queries; be transparent about data limitations in write-up |
| Render free tier cold starts | Slow first load | Add loading state in frontend; mention in README; consider Railway if needed |
| Supabase free tier limits (500 MB) | DB fills up | Monitor size; aggregate old hourly data into daily; prune old order snapshots |
| Prediction accuracy is low | Weak ML story | This is actually fine — document it honestly. Showing that a random walk is hard to beat is a valid statistical finding. Emphasize methodology over accuracy. |
| Scope creep | Not finished in 8 weekends | Stick to the plan. The MVP is: data pipeline + 1 GLM + 1 ML model + 3-page frontend. Everything else is polish. |

---

## 10. Interview Talking Points

This project gives you concrete answers to common interview questions:

- **"Walk me through an end-to-end project."** → The entire AlbionEdge pipeline: data acquisition → statistical modeling → ML → API → frontend → deployment.
- **"How do you handle data leakage?"** → Walk-forward CV, feature audit checklist, temporal train/test splits.
- **"Tell me about a hypothesis test you ran."** → LRT for city effects in the Gamma GLM, ADF test for spread stationarity, Chow test for structural breaks at patch dates.
- **"How do you choose between models?"** → Logistic regression for interpretability and inference, XGBoost for prediction performance. Compare on calibration (not just accuracy). Use the right tool for the right question.
- **"How do you handle messy real-world data?"** → AODP data has gaps, stale prices, variable update frequency. Document how you handled each issue.
- **"Tell me about your software engineering practices."** → CI/CD, type hints, Pydantic validation, Docker, tests, clean repo structure.
- **"What would you do with more time?"** → Real-time WebSocket price streaming, crafting chain optimization (LP problem), guild-level portfolio tracking, mobile app.

---

## 11. Stretch Goals (if ahead of schedule)

- **Crafting profitability calculator:** Use crafting recipes + current prices to compute expected profit with CI, factoring in resource return rates and focus cost.
- **Black Market demand prediction:** Model NPC buy order patterns to predict which items the Black Market will demand next.
- **Gold price forecasting:** ARIMA or Prophet model for gold-silver exchange rate.
- **Discord bot:** Post daily signals to a Discord channel via webhook.
- **User accounts:** Let users save watchlists (adds auth complexity — only if time permits).
