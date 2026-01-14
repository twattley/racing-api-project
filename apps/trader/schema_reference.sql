-- live_betting schema - simplified reference
-- Last updated: 2026-01-14

--------------------------------------------------------------------------------
-- TABLES
--------------------------------------------------------------------------------

-- Your bet selections (what you want to bet on)
CREATE TABLE live_betting.selections (
    unique_id           VARCHAR(255) PRIMARY KEY,
    race_id             INTEGER NOT NULL,
    race_time           TIMESTAMP NOT NULL,
    race_date           DATE NOT NULL,
    horse_id            INTEGER NOT NULL,
    horse_name          VARCHAR(255) NOT NULL,
    selection_type      VARCHAR(50) NOT NULL,      -- BACK / LAY
    market_type         VARCHAR(50) NOT NULL,      -- WIN / PLACE
    market_id           VARCHAR(255),              -- Betfair market ID
    selection_id        BIGINT,                    -- Betfair selection ID
    requested_odds      NUMERIC(8,2) NOT NULL,
    stake_points        NUMERIC,                   -- Multiplier (1.0 = normal)
    valid               BOOLEAN,
    invalidated_at      TIMESTAMP,
    invalidated_reason  TEXT,
    size_matched        NUMERIC(15,2),
    average_price_matched NUMERIC(8,2),
    cashed_out          BOOLEAN,
    fully_matched       BOOLEAN,
    customer_strategy_ref VARCHAR(255),
    created_at          TIMESTAMP DEFAULT NOW(),
    processed_at        TIMESTAMP DEFAULT NOW()
);

-- Market snapshot when selection was made
CREATE TABLE live_betting.market_state (
    unique_id           VARCHAR(132),
    selection_id        INTEGER NOT NULL,
    horse_id            INTEGER,
    race_id             INTEGER NOT NULL,
    race_date           DATE NOT NULL,
    race_time           TIMESTAMP,
    market_id_win       VARCHAR(255) NOT NULL,
    market_id_place     VARCHAR(255) NOT NULL,
    number_of_runners   INTEGER NOT NULL,          -- CRITICAL: original count
    back_price_win      NUMERIC(8,2) NOT NULL,     -- Price at selection time
    created_at          TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(unique_id, selection_id)
);

-- Live Betfair prices (refreshed every loop)
CREATE TABLE live_betting.updated_price_data (
    unique_id               VARCHAR(132) PRIMARY KEY,
    race_time               TIMESTAMP,
    race_date               DATE,
    course                  VARCHAR(100),
    horse_name              VARCHAR(255),
    selection_id            INTEGER,
    status                  VARCHAR(50),           -- ACTIVE / REMOVED
    current_runner_count    INTEGER,               -- Active runners in this market
    -- WIN market
    market_id_win           VARCHAR(32),
    betfair_win_sp          NUMERIC(8,2),
    back_price_1_win        NUMERIC(8,2),
    back_price_1_depth_win  NUMERIC(15,2),
    back_price_2_win        NUMERIC(8,2),
    back_price_2_depth_win  NUMERIC(15,2),
    lay_price_1_win         NUMERIC(8,2),
    lay_price_1_depth_win   NUMERIC(15,2),
    lay_price_2_win         NUMERIC(8,2),
    lay_price_2_depth_win   NUMERIC(15,2),
    -- PLACE market
    market_id_place         VARCHAR(255),
    market_place            VARCHAR(255),
    betfair_place_sp        NUMERIC(8,2),
    back_price_1_place      NUMERIC(8,2),
    back_price_1_depth_place NUMERIC(15,2),
    back_price_2_place      NUMERIC(8,2),
    back_price_2_depth_place NUMERIC(15,2),
    lay_price_1_place       NUMERIC(8,2),
    lay_price_1_depth_place NUMERIC(15,2),
    lay_price_2_place       NUMERIC(8,2),
    lay_price_2_depth_place NUMERIC(15,2),
    created_at              TIMESTAMP
);

-- Individual bet records (append-only, source of truth)
CREATE TABLE live_betting.bet_log (
    id                  SERIAL PRIMARY KEY,
    selection_unique_id VARCHAR(255) NOT NULL REFERENCES live_betting.selections(unique_id),
    
    -- Betfair references
    bet_id              VARCHAR(255),              -- Betfair's bet ID
    market_id           VARCHAR(255) NOT NULL,
    selection_id        BIGINT NOT NULL,
    side                VARCHAR(10) NOT NULL,      -- BACK / LAY
    
    -- What we requested
    requested_price     NUMERIC(8,2) NOT NULL,
    requested_size      NUMERIC(15,2) NOT NULL,
    
    -- Current state (updated when we poll Betfair)
    matched_size        NUMERIC(15,2) DEFAULT 0,
    matched_price       NUMERIC(8,2),
    size_remaining      NUMERIC(15,2),             -- Still waiting in market
    size_lapsed         NUMERIC(15,2) DEFAULT 0,   -- Expired unmatched (market closed)
    size_cancelled      NUMERIC(15,2) DEFAULT 0,
    
    -- Betfair status
    betfair_status      VARCHAR(30),               -- EXECUTABLE / EXECUTION_COMPLETE
    
    -- Our lifecycle status
    status              VARCHAR(20) DEFAULT 'PLACED',
    -- PLACED      = Just sent to Betfair
    -- LIVE        = In market (EXECUTABLE), may be partially matched
    -- MATCHED     = Fully matched (size_remaining = 0)
    -- CANCELLED   = We cancelled it
    -- LAPSED      = Market closed, unmatched portion lost
    -- EXPIRED     = We expired it (our 5-min rule)
    
    -- Timestamps
    placed_at           TIMESTAMP DEFAULT NOW(),
    matched_at          TIMESTAMP,                 -- When fully matched
    cancelled_at        TIMESTAMP,
    expires_at          TIMESTAMP,                 -- Our expiry time (placed_at + interval)
    
    -- Settlement (filled in after race)
    bet_outcome         VARCHAR(20),               -- WON / LOST / VOID
    profit              NUMERIC(10,2),
    commission          NUMERIC(8,2)
);

CREATE INDEX idx_bet_log_selection ON live_betting.bet_log(selection_unique_id);
CREATE INDEX idx_bet_log_status ON live_betting.bet_log(status);
CREATE INDEX idx_bet_log_placed_at ON live_betting.bet_log(placed_at);

--------------------------------------------------------------------------------
-- TABLES TO DROP (will be replaced by views)
--------------------------------------------------------------------------------

-- Settled bets with P&L (TO BE REPLACED BY VIEW)
CREATE TABLE live_betting.live_results (
    unique_id           VARCHAR(132) PRIMARY KEY,
    race_id             VARCHAR(132),
    race_time           TIMESTAMP,
    race_date           DATE,
    horse_id            INTEGER,
    horse_name          VARCHAR(132),
    selection_type      VARCHAR(132),
    market_type         VARCHAR(132),
    market_id           VARCHAR(132),
    selection_id        INTEGER,
    requested_odds      NUMERIC(8,2),
    valid               BOOLEAN,
    invalidated_at      TIMESTAMP,
    invalidated_reason  VARCHAR(132),
    size_matched        NUMERIC(8,2),
    average_price_matched NUMERIC(8,2),
    cashed_out          BOOLEAN,
    fully_matched       BOOLEAN,
    customer_strategy_ref VARCHAR(132),
    created_at          TIMESTAMP,
    processed_at        TIMESTAMP,
    bet_outcome         VARCHAR(132),              -- WON / LOST / TO_BE_RUN
    price_matched       NUMERIC(8,2),
    profit              NUMERIC(8,2),
    commission          NUMERIC(8,2),
    side                VARCHAR(32) NOT NULL
);

-- Pending bets (TO_BE_RUN)
CREATE TABLE live_betting.upcoming_bets (
    -- Same structure as live_results
    unique_id           VARCHAR(132) PRIMARY KEY,
    -- ... (identical columns to live_results)
    side                VARCHAR(32) NOT NULL
);

-- Contender status for value calculations
CREATE TABLE live_betting.contender_selections (
    id          SERIAL PRIMARY KEY,
    horse_id    INTEGER NOT NULL,
    horse_name  VARCHAR(255) NOT NULL,
    race_id     INTEGER NOT NULL,
    race_date   DATE NOT NULL,
    race_time   VARCHAR(50),
    status      VARCHAR(20) NOT NULL,              -- 'contender' / 'not-contender'
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(horse_id, race_id)
);

-- Market name mappings (Betfair/Matchbook/Betdaq)
CREATE TABLE live_betting.market_types (
    id              INTEGER PRIMARY KEY,
    mb_market_name  VARCHAR(64) UNIQUE,
    bf_market_name  VARCHAR(64) UNIQUE,
    bd_market_name  VARCHAR(64) UNIQUE
);

--------------------------------------------------------------------------------
-- VIEWS
--------------------------------------------------------------------------------

-- Today's valid selections
CREATE VIEW live_betting.todays_selections AS
SELECT race_time, horse_name, selection_type, market_type, 
       requested_odds, size_matched, average_price_matched
FROM live_betting.selections
WHERE race_date = CURRENT_DATE 
  AND valid = TRUE 
  AND cashed_out = FALSE
ORDER BY race_time;

-- Future price data only
CREATE VIEW live_betting.updated_price_data_vw AS
SELECT race_time, status, market_id_win, selection_id, 
       betfair_win_sp, betfair_place_sp, market_id_place, 
       created_at, unique_id
FROM live_betting.updated_price_data
WHERE race_time > CURRENT_TIMESTAMP;

--------------------------------------------------------------------------------
-- KEY RELATIONSHIPS
--------------------------------------------------------------------------------

-- live_betting.selections.unique_id       → live_betting.market_state.unique_id
-- live_betting.selections.unique_id       → live_betting.bet_log.selection_unique_id
-- live_betting.selections.selection_id    → live_betting.updated_price_data.selection_id
-- live_betting.selections.market_id       → live_betting.updated_price_data.market_id_win (for WIN)
--                                         → live_betting.updated_price_data.market_id_place (for PLACE)
-- live_betting.market_state.market_id_win → live_betting.updated_price_data.market_id_win

--------------------------------------------------------------------------------
-- NEW VIEWS
--------------------------------------------------------------------------------

-- TRADER INPUT: Everything needed to make betting decisions
CREATE VIEW live_betting.v_selection_state AS
SELECT
    -- Selection identity
    s.unique_id,
    s.race_id,
    s.race_time,
    s.race_date,
    s.horse_id,
    s.horse_name,
    
    -- What we want to bet
    s.selection_type,           -- BACK / LAY
    s.market_type,              -- WIN / PLACE
    s.requested_odds,
    s.stake_points,
    
    -- Betfair identifiers
    s.market_id,
    s.selection_id,
    
    -- Validation state
    s.valid,
    s.invalidated_reason,
    
    -- Original market snapshot (for validation rules)
    ms.number_of_runners AS original_runners,
    ms.back_price_win AS original_price,
    
    -- Current live prices (best price only)
    CASE 
        WHEN s.market_type = 'WIN' THEN p.back_price_1_win
        ELSE p.back_price_1_place
    END AS current_back_price,
    CASE 
        WHEN s.market_type = 'WIN' THEN p.lay_price_1_win
        ELSE p.lay_price_1_place
    END AS current_lay_price,
    
    -- Runner status
    p.status AS runner_status,  -- ACTIVE / REMOVED
    
    -- Current runner count (for 8→7 validation)
    p.current_runner_count AS current_runners,
    
    -- Betting progress (aggregated from bet_log)
    COALESCE(bl.total_matched, 0) AS total_matched,
    COALESCE(bl.bet_count, 0) AS bet_count,
    bl.latest_bet_status,
    bl.latest_expires_at,
    
    -- Derived: has any bet been placed?
    COALESCE(bl.bet_count, 0) > 0 AS has_bet,
    
    -- Derived: is fully matched?
    s.fully_matched

FROM live_betting.selections s

LEFT JOIN live_betting.market_state ms 
    ON s.unique_id = ms.unique_id

LEFT JOIN live_betting.updated_price_data p 
    ON s.selection_id = p.selection_id
    AND s.market_id = CASE 
        WHEN s.market_type = 'WIN' THEN p.market_id_win 
        ELSE p.market_id_place 
    END

LEFT JOIN (
    SELECT 
        selection_unique_id,
        SUM(matched_size) AS total_matched,
        COUNT(*) AS bet_count,
        MAX(status) AS latest_bet_status,
        MAX(expires_at) AS latest_expires_at
    FROM live_betting.bet_log
    GROUP BY selection_unique_id
) bl ON s.unique_id = bl.selection_unique_id

WHERE s.race_date = CURRENT_DATE
  AND s.race_time > NOW();

-- TODO: v_upcoming_bets    = Replaces upcoming_bets table (API reads)
-- TODO: v_live_results     = Replaces live_results table (API reads)
-- ============================================================================
-- STAKING TABLES
-- ============================================================================

-- Single row config for max stakes
CREATE TABLE live_betting.staking_config (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    max_back        NUMERIC(8,2) NOT NULL,
    max_lay         NUMERIC(8,2) NOT NULL,
    
    CONSTRAINT single_row CHECK (id = 1)
);

-- Shared progression tiers
CREATE TABLE live_betting.staking_tiers (
    minutes_threshold  INTEGER PRIMARY KEY,
    multiplier         NUMERIC(5,4) NOT NULL
);

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Max stakes
INSERT INTO live_betting.staking_config (id, max_back, max_lay)
VALUES (1, 50.00, 75.00);

-- Tiers (multiplier = current_back_stake / 50)
INSERT INTO live_betting.staking_tiers (minutes_threshold, multiplier) VALUES
(480, 0.04),   -- £2 / £3
(420, 0.06),   -- £3 / £4.50
(360, 0.08),   -- £4 / £6
(300, 0.12),   -- £6 / £9
(240, 0.16),   -- £8 / £12
(210, 0.20),   -- £10 / £15
(180, 0.24),   -- £12 / £18
(150, 0.32),   -- £16 / £24
(120, 0.40),   -- £20 / £30
(105, 0.48),   -- £24 / £36
(90,  0.56),   -- £28 / £42
(75,  0.64),   -- £32 / £48
(60,  0.72),   -- £36 / £54
(50,  0.80),   -- £40 / £60
(45,  0.88),   -- £44 / £66
(40,  0.92),   -- £46 / £69
(35,  0.96),   -- £48 / £72
(30,  1.00);   -- £50 / £75

-- ============================================================================
-- UPDATED VIEW (drop and recreate)
-- ============================================================================

DROP VIEW IF EXISTS live_betting.v_selection_state;

CREATE VIEW live_betting.v_selection_state AS
SELECT
    -- Selection identity
    s.unique_id,
    s.race_id,
    s.race_time,
    s.race_date,
    s.horse_id,
    s.horse_name,
    
    -- What we want to bet
    s.selection_type,
    s.market_type,
    s.requested_odds,
    s.stake_points,
    
    -- Betfair identifiers
    s.market_id,
    s.selection_id,
    
    -- Validation state
    s.valid,
    s.invalidated_reason,
    
    -- Original market snapshot
    ms.number_of_runners AS original_runners,
    ms.back_price_win AS original_price,
    
    -- Current live prices
    CASE 
        WHEN s.market_type = 'WIN' THEN p.back_price_1_win
        ELSE p.back_price_1_place
    END AS current_back_price,
    CASE 
        WHEN s.market_type = 'WIN' THEN p.lay_price_1_win
        ELSE p.lay_price_1_place
    END AS current_lay_price,
    
    -- Runner status
    p.status AS runner_status,
    p.current_runner_count AS current_runners,
    
    -- Betting progress
    COALESCE(bl.total_matched, 0) AS total_matched,
    COALESCE(bl.bet_count, 0) AS bet_count,
    bl.latest_bet_status,
    bl.latest_expires_at,
    COALESCE(bl.bet_count, 0) > 0 AS has_bet,
    s.fully_matched,
    
    -- Calculated stake (from tier lookup)
    ROUND(
        tier.multiplier * CASE 
            WHEN s.selection_type = 'BACK' THEN cfg.max_back
            ELSE cfg.max_lay
        END * COALESCE(s.stake_points, 1.0),
        2
    ) AS calculated_stake,
    
    -- Time info
    EXTRACT(EPOCH FROM (s.race_time - NOW())) / 60 AS minutes_to_race

FROM live_betting.selections s

LEFT JOIN live_betting.market_state ms 
    ON s.unique_id = ms.unique_id

LEFT JOIN live_betting.updated_price_data p 
    ON s.selection_id = p.selection_id
    AND s.market_id = CASE 
        WHEN s.market_type = 'WIN' THEN p.market_id_win 
        ELSE p.market_id_place 
    END

LEFT JOIN (
    SELECT 
        selection_unique_id,
        SUM(matched_size) AS total_matched,
        COUNT(*) AS bet_count,
        MAX(status) AS latest_bet_status,
        MAX(expires_at) AS latest_expires_at
    FROM live_betting.bet_log
    GROUP BY selection_unique_id
) bl ON s.unique_id = bl.selection_unique_id

-- Staking config (single row)
CROSS JOIN live_betting.staking_config cfg

-- Find matching tier
LEFT JOIN LATERAL (
    SELECT multiplier
    FROM live_betting.staking_tiers
    WHERE minutes_threshold <= EXTRACT(EPOCH FROM (s.race_time - NOW())) / 60
    ORDER BY minutes_threshold DESC
    LIMIT 1
) tier ON true

WHERE s.race_date = CURRENT_DATE
  AND s.race_time > NOW();