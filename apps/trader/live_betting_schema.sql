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
    bet_attempt_id character varying(64)
);


ALTER TABLE live_betting.bet_log OWNER TO postgres;

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
-- Name: live_results; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.live_results (
    unique_id character varying(132),
    race_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    horse_id integer,
    horse_name character varying(132),
    selection_type character varying(132),
    market_type character varying(132),
    market_id character varying(132),
    selection_id integer,
    requested_odds numeric(8,2),
    valid boolean,
    invalidated_at timestamp without time zone,
    invalidated_reason character varying(132),
    size_matched numeric(8,2),
    average_price_matched numeric(8,2),
    cashed_out boolean,
    fully_matched boolean,
    customer_strategy_ref character varying(132),
    created_at timestamp without time zone,
    processed_at timestamp without time zone,
    bet_outcome character varying(132),
    price_matched numeric(8,2),
    profit numeric(8,2),
    commission numeric(8,2),
    side character varying(32) NOT NULL
);


ALTER TABLE live_betting.live_results OWNER TO postgres;

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
    size_matched numeric(15,2),
    average_price_matched numeric(8,2),
    cashed_out boolean,
    fully_matched boolean,
    customer_strategy_ref character varying(255),
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    processed_at timestamp without time zone DEFAULT now() NOT NULL,
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
-- Name: todays_selections; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.todays_selections AS
 SELECT race_time,
    horse_name,
    selection_type,
    market_type,
    requested_odds,
    size_matched,
    average_price_matched
   FROM live_betting.selections
  WHERE ((race_date = CURRENT_DATE) AND (valid = true) AND (cashed_out = false))
  ORDER BY race_time;


ALTER VIEW live_betting.todays_selections OWNER TO postgres;

--
-- Name: upcoming_bets; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.upcoming_bets (
    unique_id character varying(132),
    race_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    horse_id integer,
    horse_name character varying(132),
    selection_type character varying(132),
    market_type character varying(132),
    market_id character varying(132),
    selection_id integer,
    requested_odds numeric(8,2),
    valid boolean,
    invalidated_at timestamp without time zone,
    invalidated_reason character varying(132),
    size_matched numeric(8,2),
    average_price_matched numeric(8,2),
    cashed_out boolean,
    fully_matched boolean,
    customer_strategy_ref character varying(132),
    created_at timestamp without time zone,
    processed_at timestamp without time zone,
    bet_outcome character varying(132),
    price_matched numeric(8,2),
    profit numeric(8,2),
    commission numeric(8,2),
    side character varying(32) NOT NULL
);


ALTER TABLE live_betting.upcoming_bets OWNER TO postgres;

--
-- Name: updated_price_data; Type: TABLE; Schema: live_betting; Owner: postgres
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
-- Name: updated_price_data_vw; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.betfair_prices_vw AS
 SELECT race_time,
    status,
    market_id_win,
    selection_id,
    betfair_win_sp,
    betfair_place_sp,
    market_id_place,
    created_at,
    unique_id
   FROM live_betting.betfair_prices
  WHERE (race_time > CURRENT_TIMESTAMP);


ALTER VIEW live_betting.betfair_prices_vw OWNER TO postgres;

--
-- Name: v_selection_state; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_selection_state AS
 WITH short_price_removals AS (
         SELECT DISTINCT updated_price_data.market_id_win
           FROM live_betting.betfair_prices
          WHERE (((updated_price_data.status)::text = 'REMOVED'::text) AND (updated_price_data.back_price_1_win < 10.0) AND (updated_price_data.back_price_1_win IS NOT NULL) AND (updated_price_data.race_date = CURRENT_DATE))
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
    COALESCE(bl.total_matched, (0)::numeric) AS total_matched,
    COALESCE(bl.bet_count, (0)::bigint) AS bet_count,
    bl.latest_bet_status,
    bl.latest_expires_at,
    (COALESCE(bl.bet_count, (0)::bigint) > 0) AS has_bet,
    s.fully_matched,
    round(((tier.multiplier *
        CASE
            WHEN ((s.selection_type)::text = 'BACK'::text) THEN cfg.max_back
            ELSE cfg.max_lay
        END) * COALESCE(s.stake_points, 1.0)), 2) AS calculated_stake,
    (EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric) AS minutes_to_race,
    ((p.market_id_win)::text IN ( SELECT short_price_removals.market_id_win
           FROM short_price_removals)) AS short_price_removed
   FROM (((((live_betting.selections s
     LEFT JOIN live_betting.market_state ms ON ((((s.unique_id)::text = (ms.unique_id)::text) AND (s.selection_id = ms.selection_id))))
     LEFT JOIN live_betting.betfair_prices p ON (((s.selection_id = p.selection_id) AND ((s.market_id)::text = (
        CASE
            WHEN ((s.market_type)::text = 'WIN'::text) THEN p.market_id_win
            ELSE p.market_id_place
        END)::text))))
     LEFT JOIN ( SELECT bet_log.selection_unique_id,
            sum(bet_log.matched_size) AS total_matched,
            count(*) AS bet_count,
            max((bet_log.status)::text) AS latest_bet_status,
            max(bet_log.expires_at) AS latest_expires_at
           FROM live_betting.bet_log
          GROUP BY bet_log.selection_unique_id) bl ON (((s.unique_id)::text = (bl.selection_unique_id)::text)))
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
-- Name: bet_log id; Type: DEFAULT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log ALTER COLUMN id SET DEFAULT nextval('live_betting.bet_log_id_seq'::regclass);


--
-- Name: contender_selections id; Type: DEFAULT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.contender_selections ALTER COLUMN id SET DEFAULT nextval('live_betting.contender_selections_id_seq'::regclass);


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
-- Name: live_results live_bets_unq_id; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.live_results
    ADD CONSTRAINT live_bets_unq_id UNIQUE (unique_id);


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
-- Name: upcoming_bets upcuming_bets_unq_id; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.upcoming_bets
    ADD CONSTRAINT upcuming_bets_unq_id UNIQUE (unique_id);


--
-- Name: updated_price_data update_bf_prices_unq_id; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.betfair_prices
    ADD CONSTRAINT update_bf_prices_unq_id UNIQUE (unique_id);


--
-- Name: selections uq_selections_unique_id; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.selections
    ADD CONSTRAINT uq_selections_unique_id UNIQUE (unique_id);


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
-- Name: idx_contender_selections_race_date; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_contender_selections_race_date ON live_betting.contender_selections USING btree (race_date);


--
-- Name: idx_contender_selections_race_id; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_contender_selections_race_id ON live_betting.contender_selections USING btree (race_id);


--
-- Name: bet_log bet_log_selection_unique_id_fkey; Type: FK CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.bet_log
    ADD CONSTRAINT bet_log_selection_unique_id_fkey FOREIGN KEY (selection_unique_id) REFERENCES live_betting.selections(unique_id);


--
-- PostgreSQL database dump complete
--

