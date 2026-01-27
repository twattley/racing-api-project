--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5 (Postgres.app)
-- Dumped by pg_dump version 17.5 (Postgres.app)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: live_betting; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA live_betting;


ALTER SCHEMA live_betting OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: bet_log; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.bet_log (
    id integer NOT NULL,
    selection_unique_id character varying(255) NOT NULL,
    bet_id character varying(255),
    market_id character varying(255) NOT NULL,
    selection_id bigint NOT NULL,
    side character varying(10) NOT NULL,
    requested_price numeric(8,2) NOT NULL,
    requested_size numeric(15,2) NOT NULL,
    matched_size numeric(15,2) DEFAULT 0,
    matched_price numeric(8,2),
    size_remaining numeric(15,2),
    size_lapsed numeric(15,2) DEFAULT 0,
    size_cancelled numeric(15,2) DEFAULT 0,
    betfair_status character varying(30),
    status character varying(20) DEFAULT 'PLACED'::character varying,
    placed_at timestamp without time zone DEFAULT now(),
    matched_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    expires_at timestamp without time zone,
    bet_outcome character varying(20),
    profit numeric(10,2),
    commission numeric(8,2),
    bet_attempt_id character varying(64),
    selection_type character varying(10),
    matched_liability numeric(15,2),
    cashed_out boolean DEFAULT false
);


ALTER TABLE live_betting.bet_log OWNER TO postgres;

--
-- Name: COLUMN bet_log.status; Type: COMMENT; Schema: live_betting; Owner: postgres
--

COMMENT ON COLUMN live_betting.bet_log.status IS 'PLACED, LIVE, MATCHED, CANCELLED, LAPSED, EXPIRED, FAILED, CASHED_OUT';


--
-- Name: bet_log_id_seq; Type: SEQUENCE; Schema: live_betting; Owner: postgres
--

CREATE SEQUENCE live_betting.bet_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE live_betting.bet_log_id_seq OWNER TO postgres;

--
-- Name: bet_log_id_seq; Type: SEQUENCE OWNED BY; Schema: live_betting; Owner: postgres
--

ALTER SEQUENCE live_betting.bet_log_id_seq OWNED BY live_betting.bet_log.id;


--
-- Name: betfair_prices; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.betfair_prices (
    race_time timestamp without time zone,
    horse_name character varying(255),
    race_date date,
    course character varying(100),
    status character varying(50),
    market_id_win character varying(32),
    selection_id integer,
    betfair_win_sp numeric(8,2),
    betfair_place_sp numeric(8,2),
    back_price_1_win numeric(8,2),
    back_price_1_depth_win numeric(15,2),
    back_price_2_win numeric(8,2),
    back_price_2_depth_win numeric(15,2),
    lay_price_1_win numeric(8,2),
    lay_price_1_depth_win numeric(15,2),
    lay_price_2_win numeric(8,2),
    lay_price_2_depth_win numeric(15,2),
    market_place character varying(255),
    market_id_place character varying(255),
    back_price_1_place numeric(8,2),
    back_price_1_depth_place numeric(15,2),
    back_price_2_place numeric(8,2),
    back_price_2_depth_place numeric(15,2),
    lay_price_1_place numeric(8,2),
    lay_price_1_depth_place numeric(15,2),
    lay_price_2_place numeric(8,2),
    lay_price_2_depth_place numeric(15,2),
    created_at timestamp without time zone,
    unique_id character varying(132),
    current_runner_count integer
);


ALTER TABLE live_betting.betfair_prices OWNER TO postgres;

--
-- Name: contender_selections; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.contender_selections (
    id integer NOT NULL,
    horse_id integer NOT NULL,
    horse_name character varying(255) NOT NULL,
    race_id integer NOT NULL,
    race_date date NOT NULL,
    race_time character varying(50),
    status character varying(20) NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT contender_selections_status_check CHECK (((status)::text = ANY ((ARRAY['contender'::character varying, 'not-contender'::character varying])::text[])))
);


ALTER TABLE live_betting.contender_selections OWNER TO postgres;

--
-- Name: contender_selections_id_seq; Type: SEQUENCE; Schema: live_betting; Owner: postgres
--

CREATE SEQUENCE live_betting.contender_selections_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE live_betting.contender_selections_id_seq OWNER TO postgres;

--
-- Name: contender_selections_id_seq; Type: SEQUENCE OWNED BY; Schema: live_betting; Owner: postgres
--

ALTER SEQUENCE live_betting.contender_selections_id_seq OWNED BY live_betting.contender_selections.id;


--
-- Name: market_state; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.market_state (
    selection_id integer NOT NULL,
    back_price_win numeric(8,2) NOT NULL,
    race_id integer NOT NULL,
    race_date date NOT NULL,
    race_time timestamp without time zone,
    market_id_win character varying(255) NOT NULL,
    market_id_place character varying(255) NOT NULL,
    number_of_runners integer NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    unique_id character varying(132),
    bet_selection_id integer,
    bet_type character(16),
    market_type character varying(16),
    horse_id integer
);


ALTER TABLE live_betting.market_state OWNER TO postgres;

--
-- Name: market_types; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.market_types (
    id integer NOT NULL,
    mb_market_name character varying(64),
    bf_market_name character varying(64),
    bd_market_name character varying(64)
);


ALTER TABLE live_betting.market_types OWNER TO postgres;

--
-- Name: pending_orders; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.pending_orders (
    id integer NOT NULL,
    selection_unique_id character varying(255) NOT NULL,
    bet_id character varying(255),
    market_id character varying(255) NOT NULL,
    selection_id bigint NOT NULL,
    side character varying(10) NOT NULL,
    selection_type character varying(10),
    requested_price numeric(8,2) NOT NULL,
    requested_size numeric(15,2) NOT NULL,
    matched_size numeric(15,2) DEFAULT 0,
    matched_price numeric(8,2),
    size_remaining numeric(15,2),
    size_lapsed numeric(15,2) DEFAULT 0,
    size_cancelled numeric(15,2) DEFAULT 0,
    matched_liability numeric(15,2),
    betfair_status character varying(30),
    status character varying(20) DEFAULT 'PENDING'::character varying,
    placed_at timestamp without time zone DEFAULT now(),
    matched_at timestamp without time zone,
    updated_at timestamp without time zone DEFAULT now()
);


ALTER TABLE live_betting.pending_orders OWNER TO postgres;

--
-- Name: pending_orders_id_seq; Type: SEQUENCE; Schema: live_betting; Owner: postgres
--

CREATE SEQUENCE live_betting.pending_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE live_betting.pending_orders_id_seq OWNER TO postgres;

--
-- Name: pending_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: live_betting; Owner: postgres
--

ALTER SEQUENCE live_betting.pending_orders_id_seq OWNED BY live_betting.pending_orders.id;


--
-- Name: selections; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.selections (
    unique_id character varying(255),
    race_id integer NOT NULL,
    race_time timestamp without time zone NOT NULL,
    race_date date NOT NULL,
    horse_id integer NOT NULL,
    horse_name character varying(255) NOT NULL,
    selection_type character varying(50) NOT NULL,
    market_type character varying(50) NOT NULL,
    market_id character varying(255),
    selection_id bigint,
    requested_odds numeric(8,2) NOT NULL,
    valid boolean,
    invalidated_at timestamp without time zone,
    invalidated_reason text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    stake_points numeric
);


ALTER TABLE live_betting.selections OWNER TO postgres;

--
-- Name: staking_config; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.staking_config (
    id integer DEFAULT 1 NOT NULL,
    max_back numeric(8,2) NOT NULL,
    max_lay numeric(8,2) NOT NULL,
    CONSTRAINT single_row CHECK ((id = 1))
);


ALTER TABLE live_betting.staking_config OWNER TO postgres;

--
-- Name: staking_tiers; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.staking_tiers (
    minutes_threshold integer NOT NULL,
    multiplier numeric(5,4) NOT NULL
);


ALTER TABLE live_betting.staking_tiers OWNER TO postgres;

--
-- Name: v_bet_status; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_bet_status AS
 WITH bet_summary AS (
         SELECT bet_log.selection_unique_id,
            sum(bet_log.matched_size) AS total_matched_size,
            sum(COALESCE(bet_log.matched_liability, bet_log.matched_size)) AS total_matched_liability,
                CASE
                    WHEN (sum(bet_log.matched_size) > (0)::numeric) THEN (sum((bet_log.matched_size * bet_log.matched_price)) / sum(bet_log.matched_size))
                    ELSE NULL::numeric
                END AS average_price_matched,
            count(*) AS bet_count,
            max(bet_log.placed_at) AS latest_placed_at,
            bool_or(bet_log.cashed_out) AS cashed_out
           FROM live_betting.bet_log
          WHERE ((bet_log.status)::text <> ALL ((ARRAY['FAILED'::character varying, 'CANCELLED'::character varying])::text[]))
          GROUP BY bet_log.selection_unique_id
        ), staking AS (
         SELECT s_1.unique_id,
            round(((COALESCE(tier.multiplier, 1.0) *
                CASE
                    WHEN ((s_1.selection_type)::text = 'BACK'::text) THEN cfg.max_back
                    ELSE cfg.max_lay
                END) * COALESCE(s_1.stake_points, 1.0)), 2) AS calculated_stake
           FROM ((live_betting.selections s_1
             CROSS JOIN live_betting.staking_config cfg)
             LEFT JOIN LATERAL ( SELECT staking_tiers.multiplier
                   FROM live_betting.staking_tiers
                  WHERE ((staking_tiers.minutes_threshold)::numeric <= (EXTRACT(epoch FROM ((s_1.race_time)::timestamp with time zone - now())) / (60)::numeric))
                  ORDER BY staking_tiers.minutes_threshold DESC
                 LIMIT 1) tier ON (true))
        )
 SELECT s.unique_id,
    s.race_id,
    s.race_time,
    s.race_date,
    s.horse_id,
    s.horse_name,
    s.selection_type,
    s.market_type,
    s.market_id,
    s.selection_id,
    s.requested_odds,
    s.valid,
    s.invalidated_at,
    s.invalidated_reason,
    COALESCE(bs.total_matched_size, (0)::numeric) AS size_matched,
    bs.average_price_matched,
    COALESCE(bs.cashed_out, false) AS cashed_out,
    (COALESCE(bs.total_matched_liability, (0)::numeric) >= st.calculated_stake) AS fully_matched,
    s.selection_type AS side,
    s.created_at,
        CASE
            WHEN (s.race_time > now()) THEN 'TO_BE_RUN'::text
            WHEN (bs.total_matched_size > (0)::numeric) THEN 'PENDING_RESULT'::text
            ELSE 'NO_BET'::text
        END AS bet_outcome,
    bs.average_price_matched AS price_matched,
    NULL::numeric AS profit,
    NULL::numeric AS commission
   FROM ((live_betting.selections s
     LEFT JOIN bet_summary bs ON (((s.unique_id)::text = (bs.selection_unique_id)::text)))
     LEFT JOIN staking st ON (((s.unique_id)::text = (st.unique_id)::text)))
  WHERE (s.race_date = CURRENT_DATE);


ALTER VIEW live_betting.v_bet_status OWNER TO postgres;

--
-- Name: v_latest_betfair_prices; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_latest_betfair_prices AS
 SELECT race_time,
    horse_name,
    race_date,
    course,
    status,
    market_id_win,
    selection_id,
    betfair_win_sp,
    betfair_place_sp,
    back_price_1_win,
    back_price_1_depth_win,
    back_price_2_win,
    back_price_2_depth_win,
    lay_price_1_win,
    lay_price_1_depth_win,
    lay_price_2_win,
    lay_price_2_depth_win,
    market_place,
    market_id_place,
    back_price_1_place,
    back_price_1_depth_place,
    back_price_2_place,
    back_price_2_depth_place,
    lay_price_1_place,
    lay_price_1_depth_place,
    lay_price_2_place,
    lay_price_2_depth_place,
    created_at,
    unique_id,
    current_runner_count
   FROM ( SELECT betfair_prices.race_time,
            betfair_prices.horse_name,
            betfair_prices.race_date,
            betfair_prices.course,
            betfair_prices.status,
            betfair_prices.market_id_win,
            betfair_prices.selection_id,
            betfair_prices.betfair_win_sp,
            betfair_prices.betfair_place_sp,
            betfair_prices.back_price_1_win,
            betfair_prices.back_price_1_depth_win,
            betfair_prices.back_price_2_win,
            betfair_prices.back_price_2_depth_win,
            betfair_prices.lay_price_1_win,
            betfair_prices.lay_price_1_depth_win,
            betfair_prices.lay_price_2_win,
            betfair_prices.lay_price_2_depth_win,
            betfair_prices.market_place,
            betfair_prices.market_id_place,
            betfair_prices.back_price_1_place,
            betfair_prices.back_price_1_depth_place,
            betfair_prices.back_price_2_place,
            betfair_prices.back_price_2_depth_place,
            betfair_prices.lay_price_1_place,
            betfair_prices.lay_price_1_depth_place,
            betfair_prices.lay_price_2_place,
            betfair_prices.lay_price_2_depth_place,
            betfair_prices.created_at,
            betfair_prices.unique_id,
            betfair_prices.current_runner_count,
            row_number() OVER (PARTITION BY betfair_prices.selection_id, betfair_prices.market_id_win ORDER BY betfair_prices.created_at DESC) AS rn
           FROM live_betting.betfair_prices
          WHERE (betfair_prices.race_date = CURRENT_DATE)) ranked
  WHERE (rn = 1);


ALTER VIEW live_betting.v_latest_betfair_prices OWNER TO postgres;

--
-- Name: v_live_results; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_live_results AS
 SELECT unique_id,
    race_id,
    race_time,
    race_date,
    horse_id,
    horse_name,
    selection_type,
    market_type,
    market_id,
    selection_id,
    requested_odds,
    valid,
    invalidated_at,
    invalidated_reason,
    size_matched,
    average_price_matched,
    cashed_out,
    fully_matched,
    side,
    created_at,
    bet_outcome,
    price_matched,
    profit,
    commission
   FROM live_betting.v_bet_status
  WHERE (race_time <= now());


ALTER VIEW live_betting.v_live_results OWNER TO postgres;

--
-- Name: v_selection_state; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_selection_state AS
 WITH short_price_removals AS (
         SELECT DISTINCT lbp.market_id_win
           FROM live_betting.v_latest_betfair_prices lbp
          WHERE (((lbp.status)::text = 'REMOVED'::text) AND (lbp.back_price_1_win < 10.0) AND (lbp.back_price_1_win IS NOT NULL) AND (lbp.race_date = CURRENT_DATE))
        ), pending_order_status AS (
         SELECT pending_orders.selection_unique_id,
            true AS has_pending_order,
            pending_orders.placed_at AS pending_placed_at,
            pending_orders.matched_size AS pending_matched_size,
            pending_orders.size_remaining AS pending_size_remaining,
            pending_orders.matched_liability AS pending_matched_liability
           FROM live_betting.pending_orders
          WHERE ((pending_orders.status)::text = 'PENDING'::text)
        ), completed_bets AS (
         SELECT bet_log.selection_unique_id,
            bet_log.matched_size AS total_matched,
            bet_log.matched_liability,
            1 AS bet_count
           FROM live_betting.bet_log
          WHERE ((bet_log.status)::text = 'MATCHED'::text)
        )
 SELECT s.unique_id,
    s.race_id,
    s.race_time,
    s.race_date,
    s.horse_id,
    s.horse_name,
    s.selection_type,
    s.market_type,
    s.requested_odds,
    s.stake_points,
    s.market_id,
    s.selection_id,
    s.valid,
    s.invalidated_reason,
    ms.number_of_runners AS original_runners,
    ms.back_price_win AS original_price,
        CASE
            WHEN ((s.market_type)::text = 'WIN'::text) THEN p.back_price_1_win
            ELSE p.back_price_1_place
        END AS current_back_price,
        CASE
            WHEN ((s.market_type)::text = 'WIN'::text) THEN p.lay_price_1_win
            ELSE p.lay_price_1_place
        END AS current_lay_price,
    p.status AS runner_status,
    p.current_runner_count AS current_runners,
    (COALESCE(cb.total_matched, (0)::numeric) + COALESCE(po.pending_matched_size, (0)::numeric)) AS total_matched,
    (COALESCE(cb.matched_liability, (0)::numeric) + COALESCE(po.pending_matched_liability, (0)::numeric)) AS total_liability,
    COALESCE((cb.bet_count)::bigint, (0)::bigint) AS bet_count,
    COALESCE(po.has_pending_order, false) AS has_pending_order,
    po.pending_placed_at,
    COALESCE(po.pending_size_remaining, (0)::numeric) AS pending_size_remaining,
    ((COALESCE((cb.bet_count)::bigint, (0)::bigint) > 0) OR COALESCE(po.has_pending_order, false)) AS has_bet,
    round(((tier.multiplier *
        CASE
            WHEN ((s.selection_type)::text = 'BACK'::text) THEN cfg.max_back
            ELSE cfg.max_lay
        END) * COALESCE(s.stake_points, 1.0)), 2) AS calculated_stake,
    (EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric) AS minutes_to_race,
    ((EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric) < (2)::numeric) AS use_fill_or_kill,
        CASE
            WHEN ((s.selection_type)::text = 'BACK'::text) THEN ((COALESCE(cb.total_matched, (0)::numeric) + COALESCE(po.pending_matched_size, (0)::numeric)) <= cfg.max_back)
            ELSE ((COALESCE(cb.matched_liability, (0)::numeric) + COALESCE(po.pending_matched_liability, (0)::numeric)) <= cfg.max_lay)
        END AS within_stake_limit,
    ((p.market_id_win)::text IN ( SELECT short_price_removals.market_id_win
           FROM short_price_removals)) AS short_price_removed,
    (((s.market_type)::text = 'PLACE'::text) AND (ms.number_of_runners >= 8) AND (p.current_runner_count < 8)) AS place_terms_changed
   FROM ((((((live_betting.selections s
     LEFT JOIN live_betting.market_state ms ON ((((s.unique_id)::text = (ms.unique_id)::text) AND (s.selection_id = ms.selection_id))))
     LEFT JOIN live_betting.v_latest_betfair_prices p ON (((s.selection_id = p.selection_id) AND ((s.market_id)::text = (
        CASE
            WHEN ((s.market_type)::text = 'WIN'::text) THEN p.market_id_win
            ELSE p.market_id_place
        END)::text))))
     LEFT JOIN pending_order_status po ON (((s.unique_id)::text = (po.selection_unique_id)::text)))
     LEFT JOIN completed_bets cb ON (((s.unique_id)::text = (cb.selection_unique_id)::text)))
     CROSS JOIN live_betting.staking_config cfg)
     LEFT JOIN LATERAL ( SELECT staking_tiers.multiplier
           FROM live_betting.staking_tiers
          WHERE ((staking_tiers.minutes_threshold)::numeric <= (EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric))
          ORDER BY staking_tiers.minutes_threshold DESC
         LIMIT 1) tier ON (true))
  WHERE ((s.race_date = CURRENT_DATE) AND (s.race_time > now()));


ALTER VIEW live_betting.v_selection_state OWNER TO postgres;

--
-- Name: v_todays_results; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_todays_results AS
 SELECT bl.id,
    bl.selection_unique_id,
    bl.bet_id,
    bl.market_id,
    bl.selection_id,
    bl.side,
    bl.requested_price,
    bl.requested_size,
    bl.matched_size,
    bl.matched_price,
    bl.size_remaining,
    bl.size_lapsed,
    bl.size_cancelled,
    bl.betfair_status,
    bl.status,
    bl.placed_at,
    bl.matched_at,
    bl.cancelled_at,
    bl.expires_at,
    bl.bet_outcome,
    bl.profit,
    bl.commission,
    s.horse_name,
    s.race_time,
    s.market_type
   FROM (live_betting.bet_log bl
     JOIN live_betting.selections s ON (((bl.selection_unique_id)::text = (s.unique_id)::text)))
  WHERE ((s.race_date = CURRENT_DATE) AND (bl.bet_outcome IS NOT NULL));


ALTER VIEW live_betting.v_todays_results OWNER TO postgres;

--
-- Name: v_upcoming_bets; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_upcoming_bets AS
 SELECT unique_id,
    race_id,
    race_time,
    race_date,
    horse_id,
    horse_name,
    selection_type,
    market_type,
    market_id,
    selection_id,
    requested_odds,
    valid,
    invalidated_at,
    invalidated_reason,
    size_matched,
    average_price_matched,
    cashed_out,
    fully_matched,
    side,
    created_at,
    bet_outcome,
    price_matched,
    profit,
    commission
   FROM live_betting.v_bet_status
  WHERE (race_time > now());


ALTER VIEW live_betting.v_upcoming_bets OWNER TO postgres;

--
-- Name: bet_log id; Type: DEFAULT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log ALTER COLUMN id SET DEFAULT nextval('live_betting.bet_log_id_seq'::regclass);


--
-- Name: contender_selections id; Type: DEFAULT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.contender_selections ALTER COLUMN id SET DEFAULT nextval('live_betting.contender_selections_id_seq'::regclass);


--
-- Name: pending_orders id; Type: DEFAULT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.pending_orders ALTER COLUMN id SET DEFAULT nextval('live_betting.pending_orders_id_seq'::regclass);


--
-- Name: bet_log bet_log_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log
    ADD CONSTRAINT bet_log_pkey PRIMARY KEY (id);


--
-- Name: contender_selections contender_selections_horse_id_race_id_key; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.contender_selections
    ADD CONSTRAINT contender_selections_horse_id_race_id_key UNIQUE (horse_id, race_id);


--
-- Name: contender_selections contender_selections_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.contender_selections
    ADD CONSTRAINT contender_selections_pkey PRIMARY KEY (id);


--
-- Name: market_types market_types_bd_market_name_key; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.market_types
    ADD CONSTRAINT market_types_bd_market_name_key UNIQUE (bd_market_name);


--
-- Name: market_types market_types_bf_market_name_key; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.market_types
    ADD CONSTRAINT market_types_bf_market_name_key UNIQUE (bf_market_name);


--
-- Name: market_types market_types_mb_market_name_key; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.market_types
    ADD CONSTRAINT market_types_mb_market_name_key UNIQUE (mb_market_name);


--
-- Name: market_types market_types_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.market_types
    ADD CONSTRAINT market_types_pkey PRIMARY KEY (id);


--
-- Name: pending_orders pending_orders_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.pending_orders
    ADD CONSTRAINT pending_orders_pkey PRIMARY KEY (id);


--
-- Name: staking_config staking_config_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.staking_config
    ADD CONSTRAINT staking_config_pkey PRIMARY KEY (id);


--
-- Name: staking_tiers staking_tiers_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.staking_tiers
    ADD CONSTRAINT staking_tiers_pkey PRIMARY KEY (minutes_threshold);


--
-- Name: market_state uk_market_state_unique_selection; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.market_state
    ADD CONSTRAINT uk_market_state_unique_selection UNIQUE (unique_id, selection_id);


--
-- Name: bet_log uq_bet_log_selection; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log
    ADD CONSTRAINT uq_bet_log_selection UNIQUE (selection_unique_id);


--
-- Name: pending_orders uq_pending_orders_selection; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.pending_orders
    ADD CONSTRAINT uq_pending_orders_selection UNIQUE (selection_unique_id);


--
-- Name: selections uq_selections_unique_id; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.selections
    ADD CONSTRAINT uq_selections_unique_id UNIQUE (unique_id);


--
-- Name: idx_bet_log_bet_attempt_id; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_bet_log_bet_attempt_id ON live_betting.bet_log USING btree (bet_attempt_id);


--
-- Name: idx_bet_log_placed_at; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_bet_log_placed_at ON live_betting.bet_log USING btree (placed_at);


--
-- Name: idx_bet_log_selection; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_bet_log_selection ON live_betting.bet_log USING btree (selection_unique_id);


--
-- Name: idx_bet_log_status; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_bet_log_status ON live_betting.bet_log USING btree (status);


--
-- Name: idx_betfair_prices_selection_created; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_betfair_prices_selection_created ON live_betting.betfair_prices USING btree (selection_id, market_id_win, created_at DESC);


--
-- Name: idx_contender_selections_race_date; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_contender_selections_race_date ON live_betting.contender_selections USING btree (race_date);


--
-- Name: idx_contender_selections_race_id; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_contender_selections_race_id ON live_betting.contender_selections USING btree (race_id);


--
-- Name: idx_pending_orders_market; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_pending_orders_market ON live_betting.pending_orders USING btree (market_id, selection_id);


--
-- Name: idx_pending_orders_placed_at; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_pending_orders_placed_at ON live_betting.pending_orders USING btree (placed_at);


--
-- Name: idx_pending_orders_status; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_pending_orders_status ON live_betting.pending_orders USING btree (status);


--
-- Name: bet_log bet_log_selection_unique_id_fkey; Type: FK CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log
    ADD CONSTRAINT bet_log_selection_unique_id_fkey FOREIGN KEY (selection_unique_id) REFERENCES live_betting.selections(unique_id);


--
-- Name: pending_orders pending_orders_selection_unique_id_fkey; Type: FK CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.pending_orders
    ADD CONSTRAINT pending_orders_selection_unique_id_fkey FOREIGN KEY (selection_unique_id) REFERENCES live_betting.selections(unique_id);


--
-- PostgreSQL database dump complete
--

