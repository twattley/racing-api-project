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
    current_runner_count integer,
    sim_place_price numeric,
    sim_place_prob numeric
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
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    contender boolean,
    selection_id integer
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
         SELECT "left"((bl.selection_unique_id)::text, 11) AS base_unique_id,
            sum(bl.matched_size) AS total_matched_size,
            sum(COALESCE(bl.matched_liability, bl.matched_size)) AS total_matched_liability,
                CASE
                    WHEN (sum(bl.matched_size) > (0)::numeric) THEN (sum((bl.matched_size * bl.matched_price)) / sum(bl.matched_size))
                    ELSE NULL::numeric
                END AS average_price_matched,
            count(*) AS bet_count,
            max(bl.placed_at) AS latest_placed_at,
            bool_or(bl.cashed_out) AS cashed_out
           FROM live_betting.bet_log bl
          WHERE ((bl.status)::text <> ALL ((ARRAY['FAILED'::character varying, 'CANCELLED'::character varying])::text[]))
          GROUP BY ("left"((bl.selection_unique_id)::text, 11))
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
     LEFT JOIN bet_summary bs ON (((s.unique_id)::text = bs.base_unique_id)))
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
    current_runner_count,
    sim_place_prob,
    sim_place_price
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
            betfair_prices.sim_place_price,
            betfair_prices.sim_place_prob,
            row_number() OVER (PARTITION BY betfair_prices.selection_id, betfair_prices.market_id_win ORDER BY betfair_prices.created_at DESC) AS rn
           FROM live_betting.betfair_prices
          WHERE (betfair_prices.race_date = CURRENT_DATE)) ranked
  WHERE (rn = 1);


ALTER VIEW live_betting.v_latest_betfair_prices OWNER TO postgres;

--
-- Name: v_contender_latest_prices; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_contender_latest_prices AS
 SELECT cs.id AS contender_id,
    cs.horse_id,
    cs.race_id,
    cs.contender,
    bp.race_time,
    bp.horse_name,
    bp.race_date,
    bp.course,
    bp.status,
    bp.market_id_win,
    bp.selection_id,
    bp.betfair_win_sp,
    bp.betfair_place_sp,
    bp.back_price_1_win,
    bp.back_price_1_depth_win,
    bp.back_price_2_win,
    bp.back_price_2_depth_win,
    bp.lay_price_1_win,
    bp.lay_price_1_depth_win,
    bp.lay_price_2_win,
    bp.lay_price_2_depth_win,
    bp.market_place,
    bp.market_id_place,
    bp.back_price_1_place,
    bp.back_price_1_depth_place,
    bp.back_price_2_place,
    bp.back_price_2_depth_place,
    bp.lay_price_1_place,
    bp.lay_price_1_depth_place,
    bp.lay_price_2_place,
    bp.lay_price_2_depth_place,
    bp.created_at,
    bp.unique_id,
    bp.current_runner_count,
    bp.sim_place_prob,
    bp.sim_place_price
   FROM (live_betting.contender_selections cs
     JOIN live_betting.v_latest_betfair_prices bp ON ((((cs.horse_name)::text = (bp.horse_name)::text) AND (cs.race_date = bp.race_date))));


ALTER VIEW live_betting.v_contender_latest_prices OWNER TO postgres;

--
-- Name: v_contender_value_analysis; Type: VIEW; Schema: live_betting; Owner: postgres
--

CREATE VIEW live_betting.v_contender_value_analysis AS
 WITH race_contender_stats AS (
         SELECT contender_selections.race_id,
            count(*) FILTER (WHERE (contender_selections.contender = true)) AS num_contenders,
            count(*) FILTER (WHERE (contender_selections.contender = false)) AS num_non_contenders,
            count(*) AS total_marked
           FROM live_betting.contender_selections
          WHERE (contender_selections.race_date = CURRENT_DATE)
          GROUP BY contender_selections.race_id
        ), latest_win_prices AS (
         SELECT lbp.selection_id,
            lbp.back_price_1_win AS win_back_price,
            lbp.lay_price_1_win AS win_lay_price,
            lbp.market_id_win
           FROM live_betting.v_latest_betfair_prices lbp
        ), latest_place_prices AS (
         SELECT llp.selection_id,
            llp.market_id_place,
            llp.back_price_1_place AS place_back_price,
            llp.lay_price_1_place AS place_lay_price,
            llp.sim_place_price,
            llp.sim_place_prob
           FROM live_betting.v_latest_betfair_prices llp
        )
 SELECT cs.race_id,
    cs.race_date,
    cs.race_time,
    cs.horse_id,
    cs.horse_name,
    cs.selection_id,
    cs.contender,
    COALESCE(rs.num_contenders, (0)::bigint) AS num_contenders,
    COALESCE(rs.num_non_contenders, (0)::bigint) AS num_non_contenders,
    COALESCE(rs.total_marked, (0)::bigint) AS total_marked,
    wp.win_back_price,
    wp.win_lay_price,
    wp.market_id_win,
    ((100)::numeric / pp.place_back_price) AS place_back_prob,
    ((100)::numeric / pp.place_lay_price) AS place_lay_prob,
    pp.market_id_place,
    pp.place_back_price,
    pp.place_lay_price,
    pp.sim_place_price,
    ((100)::numeric * pp.sim_place_prob) AS sim_place_prob,
    ((NOT cs.contender) AND ((rs.num_contenders)::numeric > wp.win_back_price)) AS is_value_lay,
    (cs.contender AND ((rs.num_non_contenders)::numeric < wp.win_back_price)) AS is_value_back,
    ((NOT cs.contender) AND (pp.place_lay_price < COALESCE(pp.sim_place_price, (0)::numeric))) AS is_place_value_lay,
    (cs.contender AND (pp.place_back_price > COALESCE(pp.sim_place_price, (1000)::numeric))) AS is_place_value_back,
        CASE
            WHEN (NOT cs.contender) THEN ((rs.num_contenders)::numeric - wp.win_back_price)
            WHEN cs.contender THEN ((rs.num_non_contenders)::numeric - wp.win_back_price)
            ELSE NULL::numeric
        END AS value_margin
   FROM (((live_betting.contender_selections cs
     LEFT JOIN race_contender_stats rs ON ((cs.race_id = rs.race_id)))
     LEFT JOIN latest_win_prices wp ON ((cs.selection_id = wp.selection_id)))
     LEFT JOIN latest_place_prices pp ON ((cs.selection_id = pp.selection_id)))
  WHERE (cs.race_date = CURRENT_DATE);


ALTER VIEW live_betting.v_contender_value_analysis OWNER TO postgres;

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
        ), completed_bets AS (
         SELECT "left"((bl.selection_unique_id)::text, 11) AS base_unique_id,
            sum(COALESCE(bl.matched_size, (0)::numeric)) AS total_matched,
            sum(COALESCE(bl.matched_liability, (0)::numeric)) AS matched_liability,
            count(*) AS bet_count
           FROM live_betting.bet_log bl
          WHERE ((bl.status)::text = 'MATCHED'::text)
          GROUP BY ("left"((bl.selection_unique_id)::text, 11))
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
    COALESCE(cb.total_matched, (0)::numeric) AS total_matched,
    COALESCE(cb.matched_liability, (0)::numeric) AS total_liability,
    COALESCE(cb.bet_count, (0)::bigint) AS bet_count,
    (COALESCE(cb.bet_count, (0)::bigint) > 0) AS has_bet,
    round(((tier.multiplier *
        CASE
            WHEN ((s.selection_type)::text = 'BACK'::text) THEN cfg.max_back
            ELSE cfg.max_lay
        END) * COALESCE(s.stake_points, 1.0)), 2) AS calculated_stake,
    (EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric) AS minutes_to_race,
    ((EXTRACT(epoch FROM ((s.race_time)::timestamp with time zone - now())) / (60)::numeric) < (2)::numeric) AS use_fill_or_kill,
        CASE
            WHEN ((s.selection_type)::text = 'BACK'::text) THEN (COALESCE(cb.total_matched, (0)::numeric) <= cfg.max_back)
            ELSE (COALESCE(cb.matched_liability, (0)::numeric) <= cfg.max_lay)
        END AS within_stake_limit,
    ((p.market_id_win)::text IN ( SELECT short_price_removals.market_id_win
           FROM short_price_removals)) AS short_price_removed,
    (((s.market_type)::text = 'PLACE'::text) AND (ms.number_of_runners >= 8) AND (p.current_runner_count < 8)) AS place_terms_changed,
    ((s.invalidated_reason = 'Manual Cash Out'::text) AND (NOT s.valid)) AS cash_out_requested
   FROM (((((live_betting.selections s
     LEFT JOIN live_betting.market_state ms ON ((((s.unique_id)::text = (ms.unique_id)::text) AND (s.selection_id = ms.selection_id))))
     LEFT JOIN live_betting.v_latest_betfair_prices p ON (((s.selection_id = p.selection_id) AND ((s.market_id)::text = (
        CASE
            WHEN ((s.market_type)::text = 'WIN'::text) THEN p.market_id_win
            ELSE p.market_id_place
        END)::text))))
     LEFT JOIN completed_bets cb ON (((s.unique_id)::text = cb.base_unique_id)))
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
     JOIN live_betting.selections s ON (((s.unique_id)::text = "left"((bl.selection_unique_id)::text, 11))))
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
  WHERE ((race_time > now()) AND (valid = true));


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
-- Name: idx_bet_log_selection_prefix; Type: INDEX; Schema: live_betting; Owner: postgres
--

CREATE INDEX idx_bet_log_selection_prefix ON live_betting.bet_log USING btree ("left"((selection_unique_id)::text, 11));


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
-- PostgreSQL database dump complete
--

