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
-- Name: api; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA api;


ALTER SCHEMA api OWNER TO postgres;

--
-- Name: bf_raw; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA bf_raw;


ALTER SCHEMA bf_raw OWNER TO postgres;

--
-- Name: data_quality; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA data_quality;


ALTER SCHEMA data_quality OWNER TO postgres;

--
-- Name: entities; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA entities;


ALTER SCHEMA entities OWNER TO postgres;

--
-- Name: live_betting; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA live_betting;


ALTER SCHEMA live_betting OWNER TO postgres;

--
-- Name: monitoring; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA monitoring;


ALTER SCHEMA monitoring OWNER TO postgres;

--
-- Name: rp_raw; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA rp_raw;


ALTER SCHEMA rp_raw OWNER TO postgres;

--
-- Name: tf_raw; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA tf_raw;


ALTER SCHEMA tf_raw OWNER TO postgres;

--
-- Name: update_betting_selections_info(); Type: PROCEDURE; Schema: api; Owner: postgres
--

CREATE PROCEDURE api.update_betting_selections_info()
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO api.betting_selections_info (
        betting_type, session_id, confidence, horse_name, age, horse_sex, draw, headgear, weight_carried,
        weight_carried_lbs, extra_weight, jockey_claim, finishing_position,
        total_distance_beaten, industry_sp, betfair_win_sp, betfair_place_sp,
        official_rating, ts, rpr, tfr, tfig, in_play_high, in_play_low,
        in_race_comment, tf_comment, tfr_view, race_id, horse_id, jockey_id,
        trainer_id, owner_id, sire_id, dam_id, unique_id, race_time, race_date,
        race_title, race_type, race_class, distance, distance_yards,
        distance_meters, distance_kilometers, conditions, going,
        number_of_runners, hcap_range, age_range, surface, total_prize_money,
        first_place_prize_money, winning_time, time_seconds, relative_time,
        relative_to_standard, country, main_race_comment, meeting_id, course_id,
        course, dam, sire, trainer, jockey, created_at
    )
    WITH latest_bets AS (
        SELECT * 
        FROM api.betting_selections 
        WHERE created_at > COALESCE(
            (SELECT MAX(created_at) FROM api.betting_selections_info),
            '2000-01-01'::date
        )
    )
    SELECT 
        lb.betting_type, 
		lb.session_id,
		lb.confidence,
        pd.horse_name,
        pd.age,
        pd.horse_sex,
        pd.draw,
        pd.headgear,
        pd.weight_carried,
        pd.weight_carried_lbs,
        pd.extra_weight,
        pd.jockey_claim,
        pd.finishing_position,
        pd.total_distance_beaten,
        pd.industry_sp,
        pd.betfair_win_sp,
        pd.betfair_place_sp,
        pd.official_rating,
        pd.ts,
        pd.rpr,
        pd.tfr,
        pd.tfig,
        pd.in_play_high,
        pd.in_play_low,
        pd.in_race_comment,
        pd.tf_comment,
        pd.tfr_view,
        pd.race_id,
        pd.horse_id,
        pd.jockey_id,
        pd.trainer_id,
        pd.owner_id,
        pd.sire_id,
        pd.dam_id,
        pd.unique_id,
        pd.race_time,
        pd.race_date,
        pd.race_title,
        pd.race_type,
        pd.race_class,
        pd.distance,
        pd.distance_yards,
        pd.distance_meters,
        pd.distance_kilometers,
        pd.conditions,
        pd.going,
        pd.number_of_runners,
        pd.hcap_range,
        pd.age_range,
        pd.surface,
        pd.total_prize_money,
        pd.first_place_prize_money,
        pd.winning_time,
        pd.time_seconds,
        pd.relative_time,
        pd.relative_to_standard,
        pd.country,
        pd.main_race_comment,
        pd.meeting_id,
        pd.course_id,
        pd.course,
        pd.dam,
        pd.sire,
        pd.trainer,
        pd.jockey,
        now() as created_at 
    FROM latest_bets lb
    LEFT JOIN public.unioned_results_data pd 
    ON pd.race_id = lb.race_id 
    AND pd.horse_id = lb.horse_id
    AND pd.race_date = lb.race_date
    ON CONFLICT (unique_id, betting_type) 
    DO UPDATE SET
        horse_name = EXCLUDED.horse_name,
        age = EXCLUDED.age,
        horse_sex = EXCLUDED.horse_sex,
        draw = EXCLUDED.draw,
        headgear = EXCLUDED.headgear,
        weight_carried = EXCLUDED.weight_carried,
        weight_carried_lbs = EXCLUDED.weight_carried_lbs,
        extra_weight = EXCLUDED.extra_weight,
        jockey_claim = EXCLUDED.jockey_claim,
        finishing_position = EXCLUDED.finishing_position,
        total_distance_beaten = EXCLUDED.total_distance_beaten,
        industry_sp = EXCLUDED.industry_sp,
        betfair_win_sp = EXCLUDED.betfair_win_sp,
        betfair_place_sp = EXCLUDED.betfair_place_sp,
        official_rating = EXCLUDED.official_rating,
        ts = EXCLUDED.ts,
        rpr = EXCLUDED.rpr,
        tfr = EXCLUDED.tfr,
        tfig = EXCLUDED.tfig,
        in_play_high = EXCLUDED.in_play_high,
        in_play_low = EXCLUDED.in_play_low,
        in_race_comment = EXCLUDED.in_race_comment,
        tf_comment = EXCLUDED.tf_comment,
        tfr_view = EXCLUDED.tfr_view,
        race_id = EXCLUDED.race_id,
        horse_id = EXCLUDED.horse_id,
        jockey_id = EXCLUDED.jockey_id,
        trainer_id = EXCLUDED.trainer_id,
        owner_id = EXCLUDED.owner_id,
        sire_id = EXCLUDED.sire_id,
        dam_id = EXCLUDED.dam_id,
        race_time = EXCLUDED.race_time,
        race_date = EXCLUDED.race_date,
        race_title = EXCLUDED.race_title,
        race_type = EXCLUDED.race_type,
        race_class = EXCLUDED.race_class,
        distance = EXCLUDED.distance,
        distance_yards = EXCLUDED.distance_yards,
        distance_meters = EXCLUDED.distance_meters,
        distance_kilometers = EXCLUDED.distance_kilometers,
        conditions = EXCLUDED.conditions,
        going = EXCLUDED.going,
        number_of_runners = EXCLUDED.number_of_runners,
        hcap_range = EXCLUDED.hcap_range,
        age_range = EXCLUDED.age_range,
        surface = EXCLUDED.surface,
        total_prize_money = EXCLUDED.total_prize_money,
        first_place_prize_money = EXCLUDED.first_place_prize_money,
        winning_time = EXCLUDED.winning_time,
        time_seconds = EXCLUDED.time_seconds,
        relative_time = EXCLUDED.relative_time,
        relative_to_standard = EXCLUDED.relative_to_standard,
        country = EXCLUDED.country,
        main_race_comment = EXCLUDED.main_race_comment,
        meeting_id = EXCLUDED.meeting_id,
        course_id = EXCLUDED.course_id,
        course = EXCLUDED.course,
        dam = EXCLUDED.dam,
        sire = EXCLUDED.sire,
        trainer = EXCLUDED.trainer,
        jockey = EXCLUDED.jockey,
        created_at = EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE api.update_betting_selections_info() OWNER TO postgres;

--
-- Name: upsert_results_data(); Type: PROCEDURE; Schema: bf_raw; Owner: postgres
--

CREATE PROCEDURE bf_raw.upsert_results_data()
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO bf_raw.results_data(
		horse,
		course,
		race_time,
		race_type,
		runner_id,
		race_key,
		min_price,
		max_price,
		latest_price,
		earliest_price,
		price_change,
		non_runners,
		race_date,
		filename,
		unique_id,
		created_at

	)
    SELECT
        horse,
		course,
		race_time,
		race_type,
		runner_id,
		race_key,
		min_price,
		max_price,
		latest_price,
		earliest_price,
		price_change,
		non_runners,
		race_date,
		filename,
		unique_id,
		created_at
    FROM
        bf_raw_results_data_tmp_load
    ON CONFLICT(unique_id)
        DO UPDATE SET
            horse=EXCLUDED.horse,
			course=EXCLUDED.course,
			race_time=EXCLUDED.race_time,
			race_type=EXCLUDED.race_type,
			runner_id=EXCLUDED.runner_id,
			race_key=EXCLUDED.race_key,
			min_price=EXCLUDED.min_price,
			max_price=EXCLUDED.max_price,
			latest_price=EXCLUDED.latest_price,
			earliest_price=EXCLUDED.earliest_price,
			price_change=EXCLUDED.price_change,
			non_runners=EXCLUDED.non_runners,
			race_date=EXCLUDED.race_date,
			filename=EXCLUDED.filename,
			created_at=EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE bf_raw.upsert_results_data() OWNER TO postgres;

--
-- Name: get_my_list(); Type: FUNCTION; Schema: rp_raw; Owner: postgres
--

CREATE FUNCTION rp_raw.get_my_list() RETURNS text[]
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN ARRAY['value1', 'value2', 'value3'];
END;
$$;


ALTER FUNCTION rp_raw.get_my_list() OWNER TO postgres;

--
-- Name: upsert_results_data(); Type: PROCEDURE; Schema: rp_raw; Owner: postgres
--

CREATE PROCEDURE rp_raw.upsert_results_data()
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO rp_raw.results_data(
		race_time,
		race_date,
		course_name,
		race_class,
		horse_name,
		horse_type,
		horse_age,
		headgear,
		conditions,
		horse_price,
		race_title,
		distance,
		distance_full,
		going,
		number_of_runners,
		total_prize_money,
		first_place_prize_money,
		winning_time,
		official_rating,
		horse_weight,
		draw,
		country,
		surface,
		finishing_position,
		total_distance_beaten,
		ts_value,
		rpr_value,
		extra_weight,
		comment,
		race_time_debug,
		currency,
		course,
		jockey_name,
		jockey_claim,
		trainer_name,
		sire_name,
		dam_name,
		dams_sire,
		owner_name,
		horse_id,
		trainer_id,
		jockey_id,
		sire_id,
		dam_id,
		dams_sire_id,
		owner_id,
		race_id,
		course_id,
		meeting_id,
		unique_id,
		debug_link,
		created_at
	)
    SELECT
        race_time,
        race_date,
        course_name,
        race_class,
        horse_name,
        horse_type,
        horse_age,
        headgear,
        conditions,
        horse_price,
        race_title,
        distance,
        distance_full,
        going,
        number_of_runners,
        total_prize_money,
        first_place_prize_money,
        winning_time,
        official_rating,
        horse_weight,
        draw,
        country,
        surface,
        finishing_position,
        total_distance_beaten,
        ts_value,
        rpr_value,
        extra_weight,
        comment,
        race_time_debug,
        currency,
        course,
        jockey_name,
        jockey_claim,
        trainer_name,
        sire_name,
        dam_name,
        dams_sire,
        owner_name,
        horse_id,
        trainer_id,
        jockey_id,
        sire_id,
        dam_id,
        dams_sire_id,
        owner_id,
        race_id,
        course_id,
        meeting_id,
        unique_id,
        debug_link,
        created_at
    FROM
        rp_raw_results_data_tmp_load
    ON CONFLICT(unique_id)
        DO UPDATE SET
            race_time = EXCLUDED.race_time,
            race_date = EXCLUDED.race_date,
            course_name = EXCLUDED.course_name,
            race_class = EXCLUDED.race_class,
            horse_name = EXCLUDED.horse_name,
            horse_type = EXCLUDED.horse_type,
            horse_age = EXCLUDED.horse_age,
            headgear = EXCLUDED.headgear,
            conditions = EXCLUDED.conditions,
            horse_price = EXCLUDED.horse_price,
            race_title = EXCLUDED.race_title,
            distance = EXCLUDED.distance,
            distance_full = EXCLUDED.distance_full,
            going = EXCLUDED.going,
            number_of_runners = EXCLUDED.number_of_runners,
            total_prize_money = EXCLUDED.total_prize_money,
            first_place_prize_money = EXCLUDED.first_place_prize_money,
            winning_time = EXCLUDED.winning_time,
            official_rating = EXCLUDED.official_rating,
            horse_weight = EXCLUDED.horse_weight,
            draw = EXCLUDED.draw,
            country = EXCLUDED.country,
            surface = EXCLUDED.surface,
            finishing_position = EXCLUDED.finishing_position,
            total_distance_beaten = EXCLUDED.total_distance_beaten,
            ts_value = EXCLUDED.ts_value,
            rpr_value = EXCLUDED.rpr_value,
            extra_weight = EXCLUDED.extra_weight,
            comment = EXCLUDED.comment,
            race_time_debug = EXCLUDED.race_time_debug,
            currency = EXCLUDED.currency,
            course = EXCLUDED.course,
            jockey_name = EXCLUDED.jockey_name,
            jockey_claim = EXCLUDED.jockey_claim,
            trainer_name = EXCLUDED.trainer_name,
            sire_name = EXCLUDED.sire_name,
            dam_name = EXCLUDED.dam_name,
            dams_sire = EXCLUDED.dams_sire,
            owner_name = EXCLUDED.owner_name,
            horse_id = EXCLUDED.horse_id,
            trainer_id = EXCLUDED.trainer_id,
            jockey_id = EXCLUDED.jockey_id,
            sire_id = EXCLUDED.sire_id,
            dam_id = EXCLUDED.dam_id,
            dams_sire_id = EXCLUDED.dams_sire_id,
            owner_id = EXCLUDED.owner_id,
            race_id = EXCLUDED.race_id,
            course_id = EXCLUDED.course_id,
            meeting_id = EXCLUDED.meeting_id,
            unique_id = EXCLUDED.unique_id,
            debug_link = EXCLUDED.debug_link,
            created_at = EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE rp_raw.upsert_results_data() OWNER TO postgres;

--
-- Name: upsert_results_data_world(); Type: PROCEDURE; Schema: rp_raw; Owner: postgres
--

CREATE PROCEDURE rp_raw.upsert_results_data_world()
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO rp_raw.results_data_world(
		race_time,
		race_date,
		course_name,
		race_class,
		horse_name,
		horse_type,
		horse_age,
		headgear,
		conditions,
		horse_price,
		race_title,
		distance,
		distance_full,
		going,
		number_of_runners,
		total_prize_money,
		first_place_prize_money,
		winning_time,
		official_rating,
		horse_weight,
		draw,
		country,
		surface,
		finishing_position,
		total_distance_beaten,
		ts_value,
		rpr_value,
		extra_weight,
		comment,
		race_time_debug,
		currency,
		course,
		jockey_name,
		jockey_claim,
		trainer_name,
		sire_name,
		dam_name,
		dams_sire,
		owner_name,
		horse_id,
		trainer_id,
		jockey_id,
		sire_id,
		dam_id,
		dams_sire_id,
		owner_id,
		race_id,
		course_id,
		meeting_id,
		unique_id,
		debug_link,
		created_at
	)
    SELECT
        race_time,
        race_date,
        course_name,
        race_class,
        horse_name,
        horse_type,
        horse_age,
        headgear,
        conditions,
        horse_price,
        race_title,
        distance,
        distance_full,
        going,
        number_of_runners,
        total_prize_money,
        first_place_prize_money,
        winning_time,
        official_rating,
        horse_weight,
        draw,
        country,
        surface,
        finishing_position,
        total_distance_beaten,
        ts_value,
        rpr_value,
        extra_weight,
        comment,
        race_time_debug,
        currency,
        course,
        jockey_name,
        jockey_claim,
        trainer_name,
        sire_name,
        dam_name,
        dams_sire,
        owner_name,
        horse_id,
        trainer_id,
        jockey_id,
        sire_id,
        dam_id,
        dams_sire_id,
        owner_id,
        race_id,
        course_id,
        meeting_id,
        unique_id,
        debug_link,
        created_at
    FROM
        rp_raw_results_data_world_tmp_load
    ON CONFLICT(unique_id)
        DO UPDATE SET
            race_time = EXCLUDED.race_time,
            race_date = EXCLUDED.race_date,
            course_name = EXCLUDED.course_name,
            race_class = EXCLUDED.race_class,
            horse_name = EXCLUDED.horse_name,
            horse_type = EXCLUDED.horse_type,
            horse_age = EXCLUDED.horse_age,
            headgear = EXCLUDED.headgear,
            conditions = EXCLUDED.conditions,
            horse_price = EXCLUDED.horse_price,
            race_title = EXCLUDED.race_title,
            distance = EXCLUDED.distance,
            distance_full = EXCLUDED.distance_full,
            going = EXCLUDED.going,
            number_of_runners = EXCLUDED.number_of_runners,
            total_prize_money = EXCLUDED.total_prize_money,
            first_place_prize_money = EXCLUDED.first_place_prize_money,
            winning_time = EXCLUDED.winning_time,
            official_rating = EXCLUDED.official_rating,
            horse_weight = EXCLUDED.horse_weight,
            draw = EXCLUDED.draw,
            country = EXCLUDED.country,
            surface = EXCLUDED.surface,
            finishing_position = EXCLUDED.finishing_position,
            total_distance_beaten = EXCLUDED.total_distance_beaten,
            ts_value = EXCLUDED.ts_value,
            rpr_value = EXCLUDED.rpr_value,
            extra_weight = EXCLUDED.extra_weight,
            comment = EXCLUDED.comment,
            race_time_debug = EXCLUDED.race_time_debug,
            currency = EXCLUDED.currency,
            course = EXCLUDED.course,
            jockey_name = EXCLUDED.jockey_name,
            jockey_claim = EXCLUDED.jockey_claim,
            trainer_name = EXCLUDED.trainer_name,
            sire_name = EXCLUDED.sire_name,
            dam_name = EXCLUDED.dam_name,
            dams_sire = EXCLUDED.dams_sire,
            owner_name = EXCLUDED.owner_name,
            horse_id = EXCLUDED.horse_id,
            trainer_id = EXCLUDED.trainer_id,
            jockey_id = EXCLUDED.jockey_id,
            sire_id = EXCLUDED.sire_id,
            dam_id = EXCLUDED.dam_id,
            dams_sire_id = EXCLUDED.dams_sire_id,
            owner_id = EXCLUDED.owner_id,
            race_id = EXCLUDED.race_id,
            course_id = EXCLUDED.course_id,
            meeting_id = EXCLUDED.meeting_id,
            unique_id = EXCLUDED.unique_id,
            debug_link = EXCLUDED.debug_link,
            created_at = EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE rp_raw.upsert_results_data_world() OWNER TO postgres;

--
-- Name: upsert_results_data(); Type: PROCEDURE; Schema: tf_raw; Owner: postgres
--

CREATE PROCEDURE tf_raw.upsert_results_data()
    LANGUAGE plpgsql
    AS $$
BEGIN
	INSERT INTO tf_raw.results_data
	(
	    tf_rating,
	    tf_speed_figure,
	    draw,
	    trainer_name,
	    trainer_id,
	    jockey_name,
	    jockey_id,
	    sire_name,
	    sire_id,
	    dam_name,
	    dam_id,
	    finishing_position,
	    horse_name,
	    horse_id,
	    horse_name_link,
	    horse_age,
	    equipment,
	    official_rating,
	    fractional_price,
	    betfair_win_sp,
	    betfair_place_sp,
	    in_play_prices,
	    tf_comment,
	    course,
	    race_date,
	    race_time_debug,
	    race_time,
	    course_id,
	    race,
	    race_id,
	    distance,
	    going,
	    prize,
	    hcap_range,
	    age_range,
	    race_type,
	    main_race_comment,
	    debug_link,
	    created_at,
	    unique_id
	)
	SELECT
		tf_rating,
		tf_speed_figure,
		draw,
		trainer_name,
		trainer_id,
		jockey_name,
		jockey_id,
		sire_name,
		sire_id,
		dam_name,
		dam_id,
		finishing_position,
		horse_name,
		horse_id,
		horse_name_link,
		horse_age,
		equipment,
		official_rating,
		fractional_price,
		betfair_win_sp,
		betfair_place_sp,
		in_play_prices,
		tf_comment,
		course,
		race_date,
		race_time_debug,
		race_time,
		course_id,
		race,
		race_id,
		distance,
		going,
		prize,
		hcap_range,
		age_range,
		race_type,
		main_race_comment,
		debug_link,
		created_at,
		unique_id
	FROM
		tf_raw_results_data_tmp_load
	ON CONFLICT(unique_id)
	DO UPDATE SET
		tf_rating = EXCLUDED.tf_rating,
		tf_speed_figure = EXCLUDED.tf_speed_figure,
		draw = EXCLUDED.draw,
		trainer_name = EXCLUDED.trainer_name,
		trainer_id = EXCLUDED.trainer_id,
		jockey_name = EXCLUDED.jockey_name,
		jockey_id = EXCLUDED.jockey_id,
		sire_name = EXCLUDED.sire_name,
		sire_id = EXCLUDED.sire_id,
		dam_name = EXCLUDED.dam_name,
		dam_id = EXCLUDED.dam_id,
		finishing_position = EXCLUDED.finishing_position,
		horse_name = EXCLUDED.horse_name,
		horse_id = EXCLUDED.horse_id,
		horse_name_link = EXCLUDED.horse_name_link,
		horse_age = EXCLUDED.horse_age,
		equipment = EXCLUDED.equipment,
		official_rating = EXCLUDED.official_rating,
		fractional_price = EXCLUDED.fractional_price,
		betfair_win_sp = EXCLUDED.betfair_win_sp,
		betfair_place_sp = EXCLUDED.betfair_place_sp,
		in_play_prices = EXCLUDED.in_play_prices,
		tf_comment = EXCLUDED.tf_comment,
		course = EXCLUDED.course,
		race_date = EXCLUDED.race_date,
		race_time = EXCLUDED.race_time,
		race_timestamp = EXCLUDED.race_timestamp,
		course_id = EXCLUDED.course_id,
		race = EXCLUDED.race,
		race_id = EXCLUDED.race_id,
		distance = EXCLUDED.distance,
		going = EXCLUDED.going,
		prize = EXCLUDED.prize,
		hcap_range = EXCLUDED.hcap_range,
		age_range = EXCLUDED.age_range,
		race_type = EXCLUDED.race_type,
		main_race_comment = EXCLUDED.main_race_comment,
		debug_link = EXCLUDED.debug_link,
		created_at = EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE tf_raw.upsert_results_data() OWNER TO postgres;

--
-- Name: upsert_results_data_world(); Type: PROCEDURE; Schema: tf_raw; Owner: postgres
--

CREATE PROCEDURE tf_raw.upsert_results_data_world()
    LANGUAGE plpgsql
    AS $$
BEGIN
	INSERT INTO tf_raw.results_data_world
	(
	    tf_rating,
	    tf_speed_figure,
	    draw,
	    trainer_name,
	    trainer_id,
	    jockey_name,
	    jockey_id,
	    sire_name,
	    sire_id,
	    dam_name,
	    dam_id,
	    finishing_position,
	    horse_name,
	    horse_id,
	    horse_name_link,
	    horse_age,
	    equipment,
	    official_rating,
	    fractional_price,
	    betfair_win_sp,
	    betfair_place_sp,
	    in_play_prices,
	    tf_comment,
	    course,
	    race_date,
	    race_time_debug,
	    race_time,
	    course_id,
	    race,
	    race_id,
	    distance,
	    going,
	    prize,
	    hcap_range,
	    age_range,
	    race_type,
	    main_race_comment,
	    debug_link,
	    created_at,
	    unique_id
	)
	SELECT
		tf_rating,
		tf_speed_figure,
		draw,
		trainer_name,
		trainer_id,
		jockey_name,
		jockey_id,
		sire_name,
		sire_id,
		dam_name,
		dam_id,
		finishing_position,
		horse_name,
		horse_id,
		horse_name_link,
		horse_age,
		equipment,
		official_rating,
		fractional_price,
		betfair_win_sp,
		betfair_place_sp,
		in_play_prices,
		tf_comment,
		course,
		race_date,
		race_time_debug,
		race_time,
		course_id,
		race,
		race_id,
		distance,
		going,
		prize,
		hcap_range,
		age_range,
		race_type,
		main_race_comment,
		debug_link,
		created_at,
		unique_id
	FROM
		tf_raw_results_data_world_tmp_load
	ON CONFLICT(unique_id)
	DO UPDATE SET
		tf_rating = EXCLUDED.tf_rating,
		tf_speed_figure = EXCLUDED.tf_speed_figure,
		draw = EXCLUDED.draw,
		trainer_name = EXCLUDED.trainer_name,
		trainer_id = EXCLUDED.trainer_id,
		jockey_name = EXCLUDED.jockey_name,
		jockey_id = EXCLUDED.jockey_id,
		sire_name = EXCLUDED.sire_name,
		sire_id = EXCLUDED.sire_id,
		dam_name = EXCLUDED.dam_name,
		dam_id = EXCLUDED.dam_id,
		finishing_position = EXCLUDED.finishing_position,
		horse_name = EXCLUDED.horse_name,
		horse_id = EXCLUDED.horse_id,
		horse_name_link = EXCLUDED.horse_name_link,
		horse_age = EXCLUDED.horse_age,
		equipment = EXCLUDED.equipment,
		official_rating = EXCLUDED.official_rating,
		fractional_price = EXCLUDED.fractional_price,
		betfair_win_sp = EXCLUDED.betfair_win_sp,
		betfair_place_sp = EXCLUDED.betfair_place_sp,
		in_play_prices = EXCLUDED.in_play_prices,
		tf_comment = EXCLUDED.tf_comment,
		course = EXCLUDED.course,
		race_date = EXCLUDED.race_date,
		race_time = EXCLUDED.race_time,
		race_timestamp = EXCLUDED.race_timestamp,
		course_id = EXCLUDED.course_id,
		race = EXCLUDED.race,
		race_id = EXCLUDED.race_id,
		distance = EXCLUDED.distance,
		going = EXCLUDED.going,
		prize = EXCLUDED.prize,
		hcap_range = EXCLUDED.hcap_range,
		age_range = EXCLUDED.age_range,
		race_type = EXCLUDED.race_type,
		main_race_comment = EXCLUDED.main_race_comment,
		debug_link = EXCLUDED.debug_link,
		created_at = EXCLUDED.created_at;
END;
$$;


ALTER PROCEDURE tf_raw.upsert_results_data_world() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: betting_selections; Type: TABLE; Schema: api; Owner: postgres
--

CREATE TABLE api.betting_selections (
    race_date date,
    race_id integer,
    horse_id integer,
    betting_type character varying(132),
    created_at timestamp without time zone,
    session_id integer,
    confidence numeric(6,2)
);


ALTER TABLE api.betting_selections OWNER TO postgres;

--
-- Name: betting_selections_info; Type: TABLE; Schema: api; Owner: postgres
--

CREATE TABLE api.betting_selections_info (
    betting_type character varying(132),
    session_id integer,
    confidence numeric(6,2),
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    price_move numeric(6,2),
    created_at timestamp with time zone
);


ALTER TABLE api.betting_selections_info OWNER TO postgres;

--
-- Name: betting_session; Type: TABLE; Schema: api; Owner: postgres
--

CREATE TABLE api.betting_session (
    session_id integer NOT NULL,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    is_active boolean DEFAULT false
);


ALTER TABLE api.betting_session OWNER TO postgres;

--
-- Name: feedback_date; Type: TABLE; Schema: api; Owner: postgres
--

CREATE TABLE api.feedback_date (
    today_date date
);


ALTER TABLE api.feedback_date OWNER TO postgres;

--
-- Name: historical_selections; Type: TABLE; Schema: api; Owner: postgres
--

CREATE TABLE api.historical_selections (
    unique_id character varying(255),
    race_id integer NOT NULL,
    race_time timestamp without time zone NOT NULL,
    race_date date NOT NULL,
    horse_id integer NOT NULL,
    horse_name character varying(255) NOT NULL,
    selection_type character varying(50) NOT NULL,
    market_type character varying(50) NOT NULL,
    market_id character varying(255) NOT NULL,
    selection_id bigint NOT NULL,
    requested_odds numeric(8,2) NOT NULL,
    valid boolean NOT NULL,
    invalidated_at timestamp with time zone,
    invalidated_reason text,
    size_matched numeric(15,2) NOT NULL,
    average_price_matched numeric(8,2),
    cashed_out boolean NOT NULL,
    fully_matched boolean NOT NULL,
    customer_strategy_ref character varying(255),
    created_at timestamp without time zone NOT NULL,
    processed_at timestamp without time zone NOT NULL
);


ALTER TABLE api.historical_selections OWNER TO postgres;

--
-- Name: raw_data; Type: TABLE; Schema: bf_raw; Owner: postgres
--

CREATE TABLE bf_raw.raw_data (
    horse_name text,
    course_name text,
    race_time timestamp without time zone,
    race_date date,
    race_type text,
    min_price double precision,
    max_price double precision,
    latest_price double precision,
    earliest_price double precision,
    price_change double precision,
    non_runners boolean,
    unique_id text,
    created_at timestamp without time zone
);


ALTER TABLE bf_raw.raw_data OWNER TO postgres;

--
-- Name: results_data; Type: TABLE; Schema: bf_raw; Owner: postgres
--

CREATE TABLE bf_raw.results_data (
    horse_name text,
    race_time timestamp without time zone,
    price_change double precision,
    unique_id text,
    horse_id text,
    race_id text,
    created_at timestamp without time zone
);


ALTER TABLE bf_raw.results_data OWNER TO postgres;

--
-- Name: today_horse; Type: TABLE; Schema: bf_raw; Owner: postgres
--

CREATE TABLE bf_raw.today_horse (
    horse_id integer,
    bf_horse_id integer,
    race_date date
);


ALTER TABLE bf_raw.today_horse OWNER TO postgres;

--
-- Name: todays_data; Type: TABLE; Schema: bf_raw; Owner: postgres
--

CREATE TABLE bf_raw.todays_data (
    race_time timestamp without time zone,
    race_date date,
    horse_id integer,
    horse_name character varying(132),
    course character varying(132),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    created_at timestamp without time zone,
    status character varying(64),
    market_id_win character varying(32),
    market_id_place character varying(32)
);


ALTER TABLE bf_raw.todays_data OWNER TO postgres;

--
-- Name: dam_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.dam_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.dam_id_seq OWNER TO postgres;

--
-- Name: dam; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.dam (
    rp_id character varying(32),
    name character varying(132),
    tf_id character varying(32),
    id integer DEFAULT nextval('entities.dam_id_seq'::regclass) NOT NULL
);


ALTER TABLE entities.dam OWNER TO postgres;

--
-- Name: results_data; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.results_data (
    race_time timestamp without time zone,
    race_date date,
    course_name character varying(132),
    race_class character varying(132),
    horse_name character varying(132),
    horse_type character varying(16),
    horse_age character varying(16),
    headgear character varying(16),
    conditions character varying(32),
    horse_price character varying(16),
    race_title text,
    distance character varying(32),
    distance_full character varying(32),
    going character varying(32),
    number_of_runners character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    official_rating character varying(16),
    horse_weight character varying(16),
    draw character varying(16),
    country character varying(16),
    surface character varying(16),
    finishing_position character varying(16),
    total_distance_beaten character varying(32),
    ts_value character varying(16),
    rpr_value character varying(16),
    extra_weight numeric(10,2),
    comment text,
    race_time_debug character varying(32),
    currency character varying(16),
    course character varying(132),
    jockey_name character varying(132),
    jockey_claim character varying(16),
    trainer_name character varying(132),
    sire_name character varying(132),
    dam_name character varying(132),
    dams_sire character varying(132),
    owner_name character varying(132),
    horse_id character varying(32),
    trainer_id character varying(32),
    jockey_id character varying(32),
    sire_id character varying(32),
    dam_id character varying(32),
    dams_sire_id character varying(32),
    owner_id character varying(32),
    race_id character varying(32),
    course_id character varying(32),
    meeting_id character varying(132),
    unique_id character varying(132),
    debug_link text,
    created_at timestamp without time zone,
    adj_total_distance_beaten character varying(16),
    rp_comment text
);


ALTER TABLE rp_raw.results_data OWNER TO postgres;

--
-- Name: missing_dams; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_dams AS
 SELECT rp.dam_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.dam ed ON (((ed.rp_id)::text = (rp.dam_id)::text)))
  WHERE ((ed.rp_id IS NULL) OR (ed.tf_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_dams OWNER TO postgres;

--
-- Name: horse_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.horse_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.horse_id_seq OWNER TO postgres;

--
-- Name: horse; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.horse (
    rp_id character varying(32),
    name character varying(132),
    tf_id character varying(32),
    id integer DEFAULT nextval('entities.horse_id_seq'::regclass) NOT NULL,
    bf_id character varying(32)
);


ALTER TABLE entities.horse OWNER TO postgres;

--
-- Name: missing_horses; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_horses AS
 SELECT rp.horse_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.horse eh ON (((eh.rp_id)::text = (rp.horse_id)::text)))
  WHERE ((eh.rp_id IS NULL) OR (eh.tf_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_horses OWNER TO postgres;

--
-- Name: jockey_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.jockey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.jockey_id_seq OWNER TO postgres;

--
-- Name: jockey; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.jockey (
    rp_id character varying(32),
    name character varying(132),
    tf_id character varying(32),
    id integer DEFAULT nextval('entities.jockey_id_seq'::regclass) NOT NULL
);


ALTER TABLE entities.jockey OWNER TO postgres;

--
-- Name: missing_jockeys; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_jockeys AS
 SELECT rp.jockey_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.jockey ej ON (((ej.rp_id)::text = (rp.jockey_id)::text)))
  WHERE ((ej.rp_id IS NULL) OR (ej.tf_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_jockeys OWNER TO postgres;

--
-- Name: owner_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.owner_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.owner_id_seq OWNER TO postgres;

--
-- Name: owner; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.owner (
    rp_id character varying(32),
    name text,
    id integer DEFAULT nextval('entities.owner_id_seq'::regclass) NOT NULL
);


ALTER TABLE entities.owner OWNER TO postgres;

--
-- Name: missing_owners; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_owners AS
 SELECT rp.owner_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.owner eo ON (((eo.rp_id)::text = (rp.owner_id)::text)))
  WHERE (eo.rp_id IS NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_owners OWNER TO postgres;

--
-- Name: results_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.results_data (
    horse_name character varying(132) NOT NULL,
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    tfr_view character varying(16),
    race_id integer NOT NULL,
    horse_id integer NOT NULL,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132) NOT NULL,
    race_time timestamp without time zone NOT NULL,
    race_date date NOT NULL,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint NOT NULL,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    created_at timestamp without time zone NOT NULL,
    rp_comment text,
    price_change numeric,
    rating integer,
    speed_figure integer,
    tf_unique_id character varying(132)
);


ALTER TABLE public.results_data OWNER TO postgres;

--
-- Name: missing_results_data; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_results_data AS
 SELECT rp.race_time,
    rp.course_name,
    rp.horse_name,
    rp.debug_link,
    rp.created_at
   FROM (rp_raw.results_data rp
     LEFT JOIN public.results_data pr ON (((rp.unique_id)::text = (pr.unique_id)::text)))
  WHERE (pr.unique_id IS NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_results_data OWNER TO postgres;

--
-- Name: results_links; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.results_links (
    race_date date,
    link_url text,
    course_name text,
    country_category smallint,
    course_id text
);


ALTER TABLE rp_raw.results_links OWNER TO postgres;

--
-- Name: missing_results_links; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_results_links AS
 SELECT rp.debug_link
   FROM (rp_raw.results_links rl
     LEFT JOIN rp_raw.results_data rp ON ((rp.debug_link = rl.link_url)))
  WHERE (rl.link_url IS NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_results_links OWNER TO postgres;

--
-- Name: sire_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.sire_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.sire_id_seq OWNER TO postgres;

--
-- Name: sire; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.sire (
    rp_id character varying(32),
    name character varying(132),
    tf_id character varying(32),
    id integer DEFAULT nextval('entities.sire_id_seq'::regclass) NOT NULL
);


ALTER TABLE entities.sire OWNER TO postgres;

--
-- Name: missing_sires; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_sires AS
 SELECT rp.sire_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.sire es ON (((es.rp_id)::text = (rp.sire_id)::text)))
  WHERE ((es.rp_id IS NULL) OR (es.tf_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_sires OWNER TO postgres;

--
-- Name: missing_todays_betfair_horse_ids; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_todays_betfair_horse_ids AS
 SELECT bf.race_time,
    bf.horse_name
   FROM (bf_raw.todays_data bf
     LEFT JOIN bf_raw.today_horse bhi ON ((bf.horse_id = bhi.bf_horse_id)))
  WHERE (((bf.status)::text = 'ACTIVE'::text) AND (bhi.bf_horse_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_todays_betfair_horse_ids OWNER TO postgres;

--
-- Name: todays_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.todays_data (
    horse_name character varying(132) NOT NULL,
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten numeric(10,2),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    tfr_view character varying(16),
    race_id integer NOT NULL,
    horse_id integer NOT NULL,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132) NOT NULL,
    race_time timestamp without time zone NOT NULL,
    race_date date NOT NULL,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint NOT NULL,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    created_at timestamp without time zone NOT NULL,
    rp_comment text,
    price_change numeric,
    rating integer,
    speed_figure integer,
    tf_unique_id character varying
);


ALTER TABLE public.todays_data OWNER TO postgres;

--
-- Name: todays_data; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.todays_data (
    race_time timestamp without time zone,
    race_date date,
    course_name character varying(132),
    race_class character varying(132),
    horse_name character varying(132),
    horse_type character varying(16),
    horse_age character varying(16),
    headgear character varying(16),
    conditions character varying(32),
    horse_price character varying(16),
    race_title text,
    distance character varying(32),
    distance_full character varying(32),
    going character varying(32),
    number_of_runners character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    official_rating character varying(16),
    horse_weight character varying(16),
    draw character varying(16),
    country character varying(16),
    surface character varying(16),
    finishing_position character varying(16),
    total_distance_beaten character varying(32),
    ts_value character varying(16),
    rpr_value character varying(16),
    extra_weight numeric(10,2),
    comment text,
    race_time_debug character varying(32),
    currency character varying(16),
    course character varying(132),
    jockey_name character varying(132),
    jockey_claim character varying(16),
    trainer_name character varying(132),
    sire_name character varying(132),
    dam_name character varying(132),
    dams_sire character varying(132),
    owner_name character varying(132),
    horse_id character varying(32),
    trainer_id character varying(32),
    jockey_id character varying(32),
    sire_id character varying(32),
    dam_id character varying(32),
    dams_sire_id character varying(32),
    owner_id character varying(32),
    race_id character varying(32),
    course_id character varying(32),
    meeting_id character varying(132),
    unique_id character varying(132),
    debug_link text,
    created_at timestamp without time zone,
    adj_total_distance_beaten character varying(16),
    rp_comment text
);


ALTER TABLE rp_raw.todays_data OWNER TO postgres;

--
-- Name: missing_todays_data; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_todays_data AS
 SELECT rp.race_time,
    rp.course_name,
    rp.horse_name,
    rp.debug_link,
    rp.created_at
   FROM (rp_raw.todays_data rp
     LEFT JOIN public.todays_data pr ON (((rp.unique_id)::text = (pr.unique_id)::text)))
  WHERE (pr.unique_id IS NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_todays_data OWNER TO postgres;

--
-- Name: todays_links; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.todays_links (
    link_url text,
    race_date date
);


ALTER TABLE rp_raw.todays_links OWNER TO postgres;

--
-- Name: missing_todays_links; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_todays_links AS
 SELECT rp.debug_link
   FROM (rp_raw.todays_links rl
     LEFT JOIN rp_raw.todays_data rp ON ((rp.debug_link = rl.link_url)))
  WHERE (rl.link_url IS NULL)
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_todays_links OWNER TO postgres;

--
-- Name: trainer_id_seq; Type: SEQUENCE; Schema: entities; Owner: postgres
--

CREATE SEQUENCE entities.trainer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE entities.trainer_id_seq OWNER TO postgres;

--
-- Name: trainer; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.trainer (
    rp_id character varying(32),
    name character varying(132),
    tf_id character varying(32),
    id integer DEFAULT nextval('entities.trainer_id_seq'::regclass) NOT NULL
);


ALTER TABLE entities.trainer OWNER TO postgres;

--
-- Name: missing_trainers; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.missing_trainers AS
 SELECT rp.trainer_id,
    rp.debug_link
   FROM (rp_raw.results_data rp
     LEFT JOIN entities.trainer et ON (((et.rp_id)::text = (rp.trainer_id)::text)))
  WHERE ((et.rp_id IS NULL) OR (et.tf_id IS NULL))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.missing_trainers OWNER TO postgres;

--
-- Name: results_data; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.results_data (
    tf_rating character varying(16),
    tf_speed_figure character varying(16),
    draw character varying(16),
    trainer_name character varying(132),
    trainer_id character varying(32),
    jockey_name character varying(132),
    jockey_id character varying(32),
    sire_name character varying(132),
    sire_id character varying(32),
    dam_name character varying(132),
    dam_id character varying(32),
    finishing_position character varying(16),
    horse_name character varying(132),
    horse_id character varying(32),
    horse_name_link character varying(132),
    horse_age character varying(16),
    equipment character varying(16),
    official_rating character varying(16),
    fractional_price character varying(64),
    betfair_win_sp character varying(16),
    betfair_place_sp character varying(16),
    in_play_prices character varying(16),
    tf_comment text,
    course text,
    race_date date,
    race_time_debug character varying(32),
    race_time timestamp without time zone,
    course_id character varying(32),
    race text,
    race_id character varying(132),
    distance character varying(32),
    going character varying(16),
    prize character varying(16),
    hcap_range character varying(16),
    age_range character varying(16),
    race_type character varying(16),
    main_race_comment text,
    debug_link text,
    created_at timestamp without time zone,
    unique_id character varying(132)
);


ALTER TABLE tf_raw.results_data OWNER TO postgres;

--
-- Name: raw_ingestion_counts; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.raw_ingestion_counts AS
 WITH rp_results_counts AS (
         SELECT results_data.race_date,
            count(DISTINCT results_data.unique_id) AS distinct_id_count
           FROM rp_raw.results_data
          WHERE (results_data.race_date >= (CURRENT_DATE - '21 days'::interval))
          GROUP BY results_data.race_date
          ORDER BY results_data.race_date DESC
        ), tf_results_counts AS (
         SELECT results_data.race_date,
            count(DISTINCT results_data.unique_id) AS distinct_id_count
           FROM tf_raw.results_data
          WHERE (results_data.race_date >= (CURRENT_DATE - '21 days'::interval))
          GROUP BY results_data.race_date
          ORDER BY results_data.race_date DESC
        ), public_results_counts AS (
         SELECT results_data.race_date,
            count(DISTINCT results_data.unique_id) AS distinct_id_count
           FROM public.results_data
          WHERE (results_data.race_date >= (CURRENT_DATE - '21 days'::interval))
          GROUP BY results_data.race_date
          ORDER BY results_data.race_date DESC
        )
 SELECT rp.race_date,
    rp.distinct_id_count AS rp_records_ingested,
    tf.distinct_id_count AS tf_records_ingested,
    pb.distinct_id_count AS pb_records_ingested,
    (rp.distinct_id_count - tf.distinct_id_count) AS raw_count_difference,
    (rp.distinct_id_count - pb.distinct_id_count) AS cns_count_difference
   FROM ((rp_results_counts rp
     LEFT JOIN tf_results_counts tf ON ((rp.race_date = tf.race_date)))
     LEFT JOIN public_results_counts pb ON ((rp.race_date = pb.race_date)))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.raw_ingestion_counts OWNER TO postgres;

--
-- Name: todays_data; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.todays_data (
    tf_rating character varying(16),
    tf_speed_figure character varying(16),
    draw character varying(16),
    trainer_name character varying(132),
    trainer_id character varying(32),
    jockey_name character varying(132),
    jockey_id character varying(32),
    sire_name character varying(132),
    sire_id character varying(32),
    dam_name character varying(132),
    dam_id character varying(32),
    finishing_position character varying(16),
    horse_name character varying(132),
    horse_id character varying(32),
    horse_name_link character varying(132),
    horse_age character varying(16),
    equipment character varying(16),
    official_rating character varying(16),
    fractional_price character varying(64),
    betfair_win_sp character varying(16),
    betfair_place_sp character varying(16),
    in_play_prices character varying(16),
    tf_comment text,
    course text,
    race_date date,
    race_time_debug character varying(32),
    race_time timestamp without time zone,
    course_id character varying(32),
    race text,
    race_id character varying(132),
    distance character varying(32),
    going character varying(16),
    prize character varying(16),
    hcap_range character varying(16),
    age_range character varying(16),
    race_type character varying(16),
    main_race_comment text,
    debug_link text,
    created_at timestamp without time zone,
    unique_id character varying(132)
);


ALTER TABLE tf_raw.todays_data OWNER TO postgres;

--
-- Name: raw_todays_ingestion_counts; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.raw_todays_ingestion_counts AS
 WITH rp_results_counts AS (
         SELECT 'TODAY RAW'::text AS data_type,
            count(DISTINCT todays_data.horse_id) AS record_count
           FROM rp_raw.todays_data
          WHERE (todays_data.race_date = CURRENT_DATE)
        ), tf_results_counts AS (
         SELECT 'TODAY RAW'::text AS data_type,
            count(DISTINCT todays_data.horse_id) AS record_count
           FROM tf_raw.todays_data
          WHERE (todays_data.race_date = CURRENT_DATE)
        ), bf_results_counts AS (
         SELECT 'TODAY RAW'::text AS data_type,
            count(DISTINCT todays_data.horse_id) AS record_count
           FROM bf_raw.todays_data
          WHERE (todays_data.race_date = CURRENT_DATE)
        )
 SELECT CURRENT_DATE AS race_date,
    rp.record_count AS rp_records_ingested,
    tf.record_count AS tf_records_ingested,
    bf.record_count AS bf_records_ingested,
    (rp.record_count - tf.record_count) AS tf_count_difference,
    (rp.record_count - bf.record_count) AS bf_count_difference
   FROM ((rp_results_counts rp
     LEFT JOIN tf_results_counts tf ON ((rp.data_type = tf.data_type)))
     LEFT JOIN bf_results_counts bf ON ((rp.data_type = bf.data_type)))
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.raw_todays_ingestion_counts OWNER TO postgres;

--
-- Name: todays_links; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.todays_links (
    link_url text,
    race_date date,
    race_type character varying(32)
);


ALTER TABLE tf_raw.todays_links OWNER TO postgres;

--
-- Name: todays_processed_links_counts; Type: MATERIALIZED VIEW; Schema: data_quality; Owner: postgres
--

CREATE MATERIALIZED VIEW data_quality.todays_processed_links_counts AS
 WITH unprocessed_rp_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS unprocessed_links
           FROM rp_raw.todays_links
          WHERE (NOT (todays_links.link_url IN ( SELECT todays_data.debug_link
                   FROM rp_raw.todays_data)))
        ), processed_rp_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS processed_links
           FROM rp_raw.todays_links
          WHERE (todays_links.link_url IN ( SELECT todays_data.debug_link
                   FROM rp_raw.todays_data))
        ), total_rp_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS total_links
           FROM rp_raw.todays_links
          WHERE (todays_links.race_date = CURRENT_DATE)
        ), rp_data AS (
         SELECT up.unprocessed_links,
            p.processed_links,
            t.total_links
           FROM ((unprocessed_rp_links up
             LEFT JOIN processed_rp_links p ON ((up.data_source = p.data_source)))
             LEFT JOIN total_rp_links t ON ((up.data_source = t.data_source)))
        ), unprocessed_tf_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS unprocessed_links
           FROM tf_raw.todays_links
          WHERE (NOT (todays_links.link_url IN ( SELECT todays_data.debug_link
                   FROM tf_raw.todays_data)))
        ), processed_tf_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS processed_links
           FROM tf_raw.todays_links
          WHERE (todays_links.link_url IN ( SELECT todays_data.debug_link
                   FROM tf_raw.todays_data))
        ), total_tf_links AS (
         SELECT 'RP'::text AS data_source,
            (count(*))::integer AS total_links
           FROM tf_raw.todays_links
          WHERE (todays_links.race_date = CURRENT_DATE)
        ), tf_data AS (
         SELECT up.unprocessed_links,
            p.processed_links,
            t.total_links
           FROM ((unprocessed_tf_links up
             LEFT JOIN processed_tf_links p ON ((up.data_source = p.data_source)))
             LEFT JOIN total_tf_links t ON ((up.data_source = t.data_source)))
        )
 SELECT rp_data.unprocessed_links,
    rp_data.processed_links,
    rp_data.total_links
   FROM rp_data
UNION
 SELECT tf_data.unprocessed_links,
    tf_data.processed_links,
    tf_data.total_links
   FROM tf_data
  WITH NO DATA;


ALTER MATERIALIZED VIEW data_quality.todays_processed_links_counts OWNER TO postgres;

--
-- Name: country; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.country (
    id integer,
    name character varying(132),
    category smallint
);


ALTER TABLE entities.country OWNER TO postgres;

--
-- Name: course; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.course (
    name character varying(132),
    id smallint,
    rp_name character varying(132),
    rp_id character varying(4),
    tf_name character varying(132),
    tf_id character varying(4),
    country_id character varying(4),
    error_id smallint,
    surface_id smallint,
    bf_name character varying(132),
    bf_id integer
);


ALTER TABLE entities.course OWNER TO postgres;

--
-- Name: matching_historical_bf_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_historical_bf_entities AS
 SELECT regexp_replace(rw.horse_name, '^\d+\.\s+'::text, ''::text) AS horse_name,
    rw.course_name,
    rw.race_time,
    rw.race_date,
    rw.min_price,
    rw.max_price,
    rw.latest_price,
    rw.earliest_price,
    rw.price_change,
    rw.non_runners,
    rw.unique_id,
    rw.created_at
   FROM (bf_raw.raw_data rw
     LEFT JOIN bf_raw.results_data rs ON ((rw.unique_id = rs.unique_id)))
  WHERE ((rs.unique_id IS NULL) AND (rw.horse_name !~ '^\d+$'::text));


ALTER VIEW entities.matching_historical_bf_entities OWNER TO postgres;

--
-- Name: matching_historical_rp_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_historical_rp_entities AS
 SELECT horse_name,
    course_name,
    horse_id,
    race_date,
    race_id
   FROM rp_raw.results_data
  WHERE (race_date IN ( SELECT DISTINCT matching_historical_bf_entities.race_date
           FROM entities.matching_historical_bf_entities));


ALTER VIEW entities.matching_historical_rp_entities OWNER TO postgres;

--
-- Name: matching_rp_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_rp_entities AS
 SELECT DISTINCT r.race_time,
    r.race_date,
    r.horse_name,
    r.official_rating,
    r.finishing_position,
    r.course,
    r.jockey_name,
    r.trainer_name,
    r.sire_name,
    r.dam_name,
    r.dams_sire,
    r.owner_name,
    r.horse_id,
    r.trainer_id,
    r.jockey_id,
    r.sire_id,
    r.dam_id,
    r.dams_sire_id,
    r.owner_id,
    ec.id AS course_id
   FROM (((((((rp_raw.results_data r
     LEFT JOIN entities.horse eh ON (((r.horse_id)::text = (eh.rp_id)::text)))
     LEFT JOIN entities.sire es ON (((r.sire_id)::text = (es.rp_id)::text)))
     LEFT JOIN entities.dam ed ON (((r.dam_id)::text = (ed.rp_id)::text)))
     LEFT JOIN entities.trainer et ON (((r.trainer_id)::text = (et.rp_id)::text)))
     LEFT JOIN entities.jockey ej ON (((r.jockey_id)::text = (ej.rp_id)::text)))
     LEFT JOIN entities.owner eo ON (((r.owner_id)::text = (eo.rp_id)::text)))
     LEFT JOIN entities.course ec ON (((r.course_id)::text = (ec.rp_id)::text)))
  WHERE ((r.unique_id IS NOT NULL) AND ((eh.rp_id IS NULL) OR (es.rp_id IS NULL) OR (ed.rp_id IS NULL) OR (et.rp_id IS NULL) OR (ej.rp_id IS NULL) OR (eo.rp_id IS NULL) OR (ec.rp_id IS NULL)))
UNION
 SELECT DISTINCT r.race_time,
    r.race_date,
    r.horse_name,
    r.official_rating,
    r.finishing_position,
    r.course,
    r.jockey_name,
    r.trainer_name,
    r.sire_name,
    r.dam_name,
    r.dams_sire,
    r.owner_name,
    r.horse_id,
    r.trainer_id,
    r.jockey_id,
    r.sire_id,
    r.dam_id,
    r.dams_sire_id,
    r.owner_id,
    ec.id AS course_id
   FROM (((((((rp_raw.todays_data r
     LEFT JOIN entities.horse eh ON (((r.horse_id)::text = (eh.rp_id)::text)))
     LEFT JOIN entities.sire es ON (((r.sire_id)::text = (es.rp_id)::text)))
     LEFT JOIN entities.dam ed ON (((r.dam_id)::text = (ed.rp_id)::text)))
     LEFT JOIN entities.trainer et ON (((r.trainer_id)::text = (et.rp_id)::text)))
     LEFT JOIN entities.jockey ej ON (((r.jockey_id)::text = (ej.rp_id)::text)))
     LEFT JOIN entities.owner eo ON (((r.owner_id)::text = (eo.rp_id)::text)))
     LEFT JOIN entities.course ec ON (((r.course_id)::text = (ec.rp_id)::text)))
  WHERE ((r.unique_id IS NOT NULL) AND ((eh.rp_id IS NULL) OR (es.rp_id IS NULL) OR (ed.rp_id IS NULL) OR (et.rp_id IS NULL) OR (ej.rp_id IS NULL) OR (eo.rp_id IS NULL) OR (ec.rp_id IS NULL)));


ALTER VIEW entities.matching_rp_entities OWNER TO postgres;

--
-- Name: matching_rp_tf_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_rp_tf_entities AS
 SELECT t.race_time,
    t.race_date,
    t.trainer_name,
    t.trainer_id,
    t.jockey_name,
    t.jockey_id,
    t.sire_name,
    t.sire_id,
    t.dam_name,
    t.dam_id,
    t.finishing_position,
    t.horse_name,
    t.horse_id,
    t.horse_age,
    ec.id AS course_id
   FROM (tf_raw.results_data t
     LEFT JOIN entities.course ec ON (((t.course_id)::text = (ec.tf_id)::text)))
  WHERE (t.race_date IN ( SELECT DISTINCT matching_rp_entities.race_date
           FROM entities.matching_rp_entities))
UNION
 SELECT t.race_time,
    t.race_date,
    t.trainer_name,
    t.trainer_id,
    t.jockey_name,
    t.jockey_id,
    t.sire_name,
    t.sire_id,
    t.dam_name,
    t.dam_id,
    t.finishing_position,
    t.horse_name,
    t.horse_id,
    t.horse_age,
    ec.id AS course_id
   FROM (tf_raw.todays_data t
     LEFT JOIN entities.course ec ON (((t.course_id)::text = (ec.tf_id)::text)));


ALTER VIEW entities.matching_rp_tf_entities OWNER TO postgres;

--
-- Name: matching_todays_bf_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_todays_bf_entities AS
 SELECT b.race_time,
    b.race_date,
    b.horse_name,
    b.horse_id,
    ec.id AS course_id,
    'BF'::text AS data_source
   FROM (bf_raw.todays_data b
     LEFT JOIN entities.course ec ON (((b.course)::text = (ec.bf_name)::text)));


ALTER VIEW entities.matching_todays_bf_entities OWNER TO postgres;

--
-- Name: matching_todays_rp_entities; Type: VIEW; Schema: entities; Owner: postgres
--

CREATE VIEW entities.matching_todays_rp_entities AS
 SELECT r.race_time,
    r.race_date,
    r.horse_name,
    eh.id AS horse_id,
    ec.id AS course_id,
    'RP'::text AS data_source
   FROM ((rp_raw.todays_data r
     LEFT JOIN entities.horse eh ON (((r.horse_id)::text = (eh.rp_id)::text)))
     LEFT JOIN entities.course ec ON (((r.course_id)::text = (ec.rp_id)::text)))
  WHERE ((ec.country_id)::text = '1'::text);


ALTER VIEW entities.matching_todays_rp_entities OWNER TO postgres;

--
-- Name: surface; Type: TABLE; Schema: entities; Owner: postgres
--

CREATE TABLE entities.surface (
    name character varying(132),
    id smallint
);


ALTER TABLE entities.surface OWNER TO postgres;

--
-- Name: combined_price_data; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.combined_price_data (
    race_time timestamp without time zone NOT NULL,
    horse_name character varying(255) NOT NULL,
    race_date date NOT NULL,
    course character varying(100) NOT NULL,
    status character varying(50) NOT NULL,
    market_id_win character varying(255) NOT NULL,
    todays_betfair_selection_id bigint NOT NULL,
    betfair_win_sp numeric(8,2),
    betfair_place_sp numeric(8,2),
    total_matched_win numeric(15,2),
    back_price_1_win numeric(8,2),
    back_price_1_depth_win numeric(15,2),
    back_price_2_win numeric(8,2),
    back_price_2_depth_win numeric(15,2),
    back_price_3_win numeric(8,2),
    back_price_3_depth_win numeric(15,2),
    back_price_4_win numeric(8,2),
    back_price_4_depth_win numeric(15,2),
    back_price_5_win numeric(8,2),
    back_price_5_depth_win numeric(15,2),
    lay_price_1_win numeric(8,2),
    lay_price_1_depth_win numeric(15,2),
    lay_price_2_win numeric(8,2),
    lay_price_2_depth_win numeric(15,2),
    lay_price_3_win numeric(8,2),
    lay_price_3_depth_win numeric(15,2),
    lay_price_4_win numeric(8,2),
    lay_price_4_depth_win numeric(15,2),
    lay_price_5_win numeric(8,2),
    lay_price_5_depth_win numeric(15,2),
    total_matched_event_win bigint NOT NULL,
    percent_back_win_book_win integer NOT NULL,
    percent_lay_win_book_win integer NOT NULL,
    market_place character varying(255) NOT NULL,
    market_id_place character varying(255) NOT NULL,
    total_matched_place numeric(15,2),
    back_price_1_place numeric(8,2),
    back_price_1_depth_place numeric(15,2),
    back_price_2_place numeric(8,2),
    back_price_2_depth_place numeric(15,2),
    back_price_3_place numeric(8,2),
    back_price_3_depth_place numeric(15,2),
    back_price_4_place numeric(8,2),
    back_price_4_depth_place numeric(15,2),
    back_price_5_place numeric(8,2),
    back_price_5_depth_place numeric(15,2),
    lay_price_1_place numeric(8,2),
    lay_price_1_depth_place numeric(15,2),
    lay_price_2_place numeric(8,2),
    lay_price_2_depth_place numeric(15,2),
    lay_price_3_place numeric(8,2),
    lay_price_3_depth_place numeric(15,2),
    lay_price_4_place numeric(8,2),
    lay_price_4_depth_place numeric(15,2),
    lay_price_5_place numeric(8,2),
    lay_price_5_depth_place numeric(15,2),
    total_matched_event_place bigint NOT NULL,
    percent_back_win_book_place integer NOT NULL,
    percent_lay_win_book_place integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    runners_unique_id bigint NOT NULL
);


ALTER TABLE live_betting.combined_price_data OWNER TO postgres;

--
-- Name: market_state; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.market_state (
    horse_name character varying(255) NOT NULL,
    selection_id bigint NOT NULL,
    back_price_win numeric(8,2) NOT NULL,
    lay_price_win numeric(8,2) NOT NULL,
    back_price_place numeric(8,2) NOT NULL,
    lay_price_place numeric(8,2) NOT NULL,
    race_id integer NOT NULL,
    race_date date NOT NULL,
    race_time timestamp without time zone NOT NULL,
    market_id_win character varying(255) NOT NULL,
    market_id_place character varying(255) NOT NULL,
    number_of_runners integer NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE live_betting.market_state OWNER TO postgres;

--
-- Name: race_results; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.race_results (
    unique_id character varying(255) NOT NULL,
    horse_name character varying(255) NOT NULL,
    age smallint NOT NULL,
    horse_sex character varying(10),
    draw numeric(5,2),
    headgear character varying(50),
    weight_carried character varying(50),
    weight_carried_lbs integer,
    extra_weight numeric(5,2),
    jockey_claim numeric(5,2),
    finishing_position character varying(20),
    total_distance_beaten character varying(50),
    industry_sp character varying(50),
    betfair_win_sp numeric(8,2),
    betfair_place_sp numeric(8,2),
    official_rating numeric(6,2),
    ts numeric(6,2),
    rpr numeric(6,2),
    tfr numeric(6,2),
    tfig numeric(6,2),
    in_play_high numeric(10,2),
    in_play_low numeric(10,2),
    price_change numeric(10,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view text,
    race_id integer NOT NULL,
    horse_id integer NOT NULL,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    race_time timestamp without time zone NOT NULL,
    race_date date NOT NULL,
    race_title character varying(255),
    race_type character varying(50),
    race_class integer,
    distance character varying(50),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions text,
    going character varying(50),
    number_of_runners integer,
    hcap_range character varying(50),
    age_range character varying(50),
    surface character varying(50),
    total_prize_money numeric(15,2),
    first_place_prize_money numeric(15,2),
    winning_time character varying(50),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(50),
    country character varying(50),
    main_race_comment text,
    meeting_id character varying(255),
    course_id integer NOT NULL,
    course character varying(100) NOT NULL,
    dam character varying(255),
    sire character varying(255),
    trainer character varying(255),
    jockey character varying(255),
    data_type character varying(50),
    todays_betfair_selection_id bigint NOT NULL
);


ALTER TABLE live_betting.race_results OWNER TO postgres;

--
-- Name: race_times; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.race_times (
    race_id integer NOT NULL,
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(255),
    race_type character varying(50),
    race_class integer,
    distance character varying(50),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions text,
    going character varying(50),
    number_of_runners integer,
    hcap_range character varying(50),
    age_range character varying(50),
    surface character varying(50),
    total_prize_money numeric(15,2),
    first_place_prize_money integer,
    course_id integer,
    course character varying(100),
    data_type character varying(50)
);


ALTER TABLE live_betting.race_times OWNER TO postgres;

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
    market_id character varying(255) NOT NULL,
    selection_id bigint NOT NULL,
    requested_odds numeric(8,2) NOT NULL,
    valid boolean NOT NULL,
    invalidated_at timestamp with time zone,
    invalidated_reason text,
    size_matched numeric(15,2) NOT NULL,
    average_price_matched numeric(8,2),
    cashed_out boolean NOT NULL,
    fully_matched boolean NOT NULL,
    customer_strategy_ref character varying(255),
    created_at timestamp without time zone NOT NULL,
    processed_at timestamp without time zone NOT NULL
);


ALTER TABLE live_betting.selections OWNER TO postgres;

--
-- Name: updated_price_data; Type: TABLE; Schema: live_betting; Owner: postgres
--

CREATE TABLE live_betting.updated_price_data (
    race_time timestamp without time zone NOT NULL,
    horse_name character varying(255) NOT NULL,
    race_date date NOT NULL,
    course character varying(100) NOT NULL,
    status character varying(50) NOT NULL,
    market_id_win character varying(32) NOT NULL,
    todays_betfair_selection_id integer NOT NULL,
    betfair_win_sp numeric(8,2),
    betfair_place_sp numeric(8,2),
    total_matched_win numeric(15,2),
    back_price_1_win numeric(8,2),
    back_price_1_depth_win numeric(15,2),
    back_price_2_win numeric(8,2),
    back_price_2_depth_win numeric(15,2),
    back_price_3_win numeric(8,2),
    back_price_3_depth_win numeric(15,2),
    back_price_4_win numeric(8,2),
    back_price_4_depth_win numeric(15,2),
    back_price_5_win numeric(8,2),
    back_price_5_depth_win numeric(15,2),
    lay_price_1_win numeric(8,2),
    lay_price_1_depth_win numeric(15,2),
    lay_price_2_win numeric(8,2),
    lay_price_2_depth_win numeric(15,2),
    lay_price_3_win numeric(8,2),
    lay_price_3_depth_win numeric(15,2),
    lay_price_4_win numeric(8,2),
    lay_price_4_depth_win numeric(15,2),
    lay_price_5_win numeric(8,2),
    lay_price_5_depth_win numeric(15,2),
    total_matched_event_win integer,
    percent_back_win_book_win integer,
    percent_lay_win_book_win integer,
    market_place character varying(255) NOT NULL,
    market_id_place character varying(255) NOT NULL,
    total_matched_place numeric(15,2),
    back_price_1_place numeric(8,2),
    back_price_1_depth_place numeric(15,2),
    back_price_2_place numeric(8,2),
    back_price_2_depth_place numeric(15,2),
    back_price_3_place numeric(8,2),
    back_price_3_depth_place numeric(15,2),
    back_price_4_place numeric(8,2),
    back_price_4_depth_place numeric(15,2),
    back_price_5_place numeric(8,2),
    back_price_5_depth_place numeric(15,2),
    lay_price_1_place numeric(8,2),
    lay_price_1_depth_place numeric(15,2),
    lay_price_2_place numeric(8,2),
    lay_price_2_depth_place numeric(15,2),
    lay_price_3_place numeric(8,2),
    lay_price_3_depth_place numeric(15,2),
    lay_price_4_place numeric(8,2),
    lay_price_4_depth_place numeric(15,2),
    lay_price_5_place numeric(8,2),
    lay_price_5_depth_place numeric(15,2),
    total_matched_event_place integer,
    percent_back_win_book_place integer,
    percent_lay_win_book_place integer,
    created_at timestamp without time zone NOT NULL,
    runners_unique_id integer NOT NULL,
    earliest_price numeric(8,2),
    latest_price numeric(8,2),
    price_change numeric(8,2)
);


ALTER TABLE live_betting.updated_price_data OWNER TO postgres;

--
-- Name: job_ids; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.job_ids (
    id smallint NOT NULL,
    stage_id smallint,
    name character varying(132) NOT NULL
);


ALTER TABLE monitoring.job_ids OWNER TO postgres;

--
-- Name: pipeline_logs; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.pipeline_logs (
    job_id bigint,
    job_name text,
    stage_id bigint,
    source_id bigint,
    log_level text,
    message text,
    date_processed date,
    created_at timestamp without time zone
);


ALTER TABLE monitoring.pipeline_logs OWNER TO postgres;

--
-- Name: pipeline_status; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.pipeline_status (
    job_id smallint,
    job_name character varying(132),
    stage_id smallint,
    source_id smallint,
    warnings integer,
    errors integer,
    success_indicator boolean,
    date_processed date,
    created_at timestamp without time zone
);


ALTER TABLE monitoring.pipeline_status OWNER TO postgres;

--
-- Name: pipeline_success; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.pipeline_success (
    job_id bigint,
    job_name text,
    stage_id bigint,
    source_id bigint,
    warnings bigint,
    errors bigint,
    success_indicator boolean,
    date_processed date,
    created_at timestamp without time zone
);


ALTER TABLE monitoring.pipeline_success OWNER TO postgres;

--
-- Name: source_ids; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.source_ids (
    id smallint NOT NULL,
    name character varying(132) NOT NULL
);


ALTER TABLE monitoring.source_ids OWNER TO postgres;

--
-- Name: stage_ids; Type: TABLE; Schema: monitoring; Owner: postgres
--

CREATE TABLE monitoring.stage_ids (
    id smallint NOT NULL,
    name character varying(132) NOT NULL
);


ALTER TABLE monitoring.stage_ids OWNER TO postgres;

--
-- Name: dam_dam_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.dam_dam_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dam_dam_id_seq OWNER TO postgres;

--
-- Name: horse_horse_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.horse_horse_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.horse_horse_id_seq OWNER TO postgres;

--
-- Name: jockey_jockey_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.jockey_jockey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jockey_jockey_id_seq OWNER TO postgres;

--
-- Name: missing_rp_results_data; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.missing_rp_results_data AS
 SELECT r.race_time AS race_timestamp,
    r.race_date,
    r.course_name,
    r.race_class,
    r.horse_name,
    r.horse_type,
    r.horse_age,
    r.headgear,
    r.conditions,
    r.horse_price,
    r.race_title,
    r.distance,
    r.distance_full,
    r.going,
    r.number_of_runners,
    r.total_prize_money,
    r.first_place_prize_money,
    r.winning_time,
    r.official_rating,
    r.horse_weight,
    r.draw,
    r.country,
    r.surface,
    r.finishing_position,
    r.total_distance_beaten,
    r.ts_value,
    r.rpr_value,
    r.extra_weight,
    r.comment,
    r.race_time_debug AS race_time,
    r.currency,
    r.course,
    r.jockey_name,
    r.jockey_claim,
    r.trainer_name,
    r.sire_name,
    r.dam_name,
    r.dams_sire,
    r.owner_name,
    r.horse_id,
    r.trainer_id,
    r.jockey_id,
    r.sire_id,
    r.dam_id,
    r.dams_sire_id,
    r.owner_id,
    r.race_id,
    r.course_id,
    r.meeting_id,
    r.unique_id,
    r.debug_link,
    r.created_at
   FROM (rp_raw.results_data r
     LEFT JOIN public.results_data pr ON (((r.unique_id)::text = (pr.unique_id)::text)))
  WHERE ((pr.unique_id IS NULL) AND (r.unique_id IS NOT NULL) AND (r.race_time > (now() - '9 years'::interval)));


ALTER VIEW public.missing_rp_results_data OWNER TO postgres;

--
-- Name: results_data_world; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.results_data_world (
    race_time timestamp without time zone,
    race_date date,
    course_name character varying(132),
    race_class character varying(132),
    horse_name character varying(132),
    horse_type character varying(32),
    horse_age character varying(16),
    headgear character varying(32),
    conditions character varying(32),
    horse_price character varying(32),
    race_title text,
    distance character varying(32),
    distance_full character varying(32),
    going character varying(32),
    number_of_runners character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    official_rating character varying(32),
    horse_weight character varying(32),
    draw character varying(32),
    country character varying(32),
    surface character varying(32),
    finishing_position character varying(32),
    total_distance_beaten character varying(32),
    ts_value character varying(32),
    rpr_value character varying(32),
    extra_weight numeric(10,2),
    comment text,
    race_time_debug character varying(32),
    currency character varying(32),
    course character varying(132),
    jockey_name character varying(132),
    jockey_claim character varying(32),
    trainer_name character varying(132),
    sire_name character varying(132),
    dam_name character varying(132),
    dams_sire character varying(132),
    owner_name character varying(132),
    horse_id character varying(32),
    trainer_id character varying(32),
    jockey_id character varying(32),
    sire_id character varying(32),
    dam_id character varying(32),
    dams_sire_id character varying(32),
    owner_id character varying(32),
    race_id character varying(32),
    course_id character varying(32),
    meeting_id character varying(132),
    unique_id character varying(132),
    debug_link text,
    created_at timestamp without time zone,
    adj_total_distance_beaten character varying(16),
    rp_comment text
);


ALTER TABLE rp_raw.results_data_world OWNER TO postgres;

--
-- Name: missing_rp_results_data_world; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.missing_rp_results_data_world AS
 WITH uk_ire_performances AS (
         SELECT r.race_time AS race_timestamp,
            r.race_date,
            r.course_name,
            r.race_class,
            r.horse_name,
            r.horse_type,
            r.horse_age,
            r.headgear,
            r.conditions,
            r.horse_price,
            r.race_title,
            r.distance,
            r.distance_full,
            r.going,
            r.number_of_runners,
            r.total_prize_money,
            r.first_place_prize_money,
            r.winning_time,
            r.official_rating,
            r.horse_weight,
            r.draw,
            r.country,
            r.surface,
            r.finishing_position,
            r.total_distance_beaten,
            r.ts_value,
            r.rpr_value,
            r.extra_weight,
            r.comment,
            r.race_time_debug AS race_time,
            r.currency,
            r.course,
            r.jockey_name,
            r.jockey_claim,
            r.trainer_name,
            r.sire_name,
            r.dam_name,
            r.dams_sire,
            r.owner_name,
            r.horse_id,
            r.trainer_id,
            r.jockey_id,
            r.sire_id,
            r.dam_id,
            r.dams_sire_id,
            r.owner_id,
            r.race_id,
            r.course_id,
            r.meeting_id,
            r.unique_id,
            r.debug_link,
            r.created_at
           FROM (rp_raw.results_data_world r
             LEFT JOIN entities.horse eh ON (((r.horse_id)::text = (eh.rp_id)::text)))
          WHERE (eh.rp_id IS NOT NULL)
        )
 SELECT u.race_timestamp,
    u.race_date,
    u.course_name,
    u.race_class,
    u.horse_name,
    u.horse_type,
    u.horse_age,
    u.headgear,
    u.conditions,
    u.horse_price,
    u.race_title,
    u.distance,
    u.distance_full,
    u.going,
    u.number_of_runners,
    u.total_prize_money,
    u.first_place_prize_money,
    u.winning_time,
    u.official_rating,
    u.horse_weight,
    u.draw,
    u.country,
    u.surface,
    u.finishing_position,
    u.total_distance_beaten,
    u.ts_value,
    u.rpr_value,
    u.extra_weight,
    u.comment,
    u.race_time,
    u.currency,
    u.course,
    u.jockey_name,
    u.jockey_claim,
    u.trainer_name,
    u.sire_name,
    u.dam_name,
    u.dams_sire,
    u.owner_name,
    u.horse_id,
    u.trainer_id,
    u.jockey_id,
    u.sire_id,
    u.dam_id,
    u.dams_sire_id,
    u.owner_id,
    u.race_id,
    u.course_id,
    u.meeting_id,
    u.unique_id,
    u.debug_link,
    u.created_at
   FROM (uk_ire_performances u
     LEFT JOIN public.results_data pr ON (((u.unique_id)::text = (pr.unique_id)::text)))
  WHERE ((pr.unique_id IS NULL) AND (u.unique_id IS NOT NULL));


ALTER VIEW public.missing_rp_results_data_world OWNER TO postgres;

--
-- Name: missing_tf_results_data; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.missing_tf_results_data AS
 SELECT t.tf_rating,
    t.tf_speed_figure,
    t.draw,
    t.trainer_name,
    t.trainer_id,
    t.jockey_name,
    t.jockey_id,
    t.sire_name,
    t.sire_id,
    t.dam_name,
    t.dam_id,
    t.finishing_position,
    t.horse_name,
    t.horse_id,
    t.horse_name_link,
    t.horse_age,
    t.equipment,
    t.official_rating,
    t.fractional_price,
    t.betfair_win_sp,
    t.betfair_place_sp,
    t.in_play_prices,
    t.tf_comment,
    t.course,
    t.race_date,
    t.race_time_debug AS race_time,
    t.race_time AS race_timestamp,
    t.course_id,
    t.race,
    t.race_id,
    t.distance,
    t.going,
    t.prize,
    t.hcap_range,
    t.age_range,
    t.race_type,
    t.main_race_comment,
    t.debug_link,
    t.created_at,
    t.unique_id
   FROM (tf_raw.results_data t
     LEFT JOIN public.results_data pr ON (((t.unique_id)::text = (pr.unique_id)::text)))
  WHERE ((pr.unique_id IS NULL) AND (t.unique_id IS NOT NULL));


ALTER VIEW public.missing_tf_results_data OWNER TO postgres;

--
-- Name: sire_sire_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.sire_sire_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sire_sire_id_seq OWNER TO postgres;

--
-- Name: trainer_trainer_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.trainer_trainer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.trainer_trainer_id_seq OWNER TO postgres;

--
-- Name: unioned_results_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_results_data (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
)
PARTITION BY RANGE (race_date);


ALTER TABLE public.unioned_results_data OWNER TO postgres;

--
-- Name: unioned_performance_data_2010; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2010 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2010 OWNER TO postgres;

--
-- Name: unioned_performance_data_2011; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2011 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2011 OWNER TO postgres;

--
-- Name: unioned_performance_data_2012; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2012 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2012 OWNER TO postgres;

--
-- Name: unioned_performance_data_2013; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2013 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2013 OWNER TO postgres;

--
-- Name: unioned_performance_data_2014; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2014 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2014 OWNER TO postgres;

--
-- Name: unioned_performance_data_2015; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2015 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2015 OWNER TO postgres;

--
-- Name: unioned_performance_data_2016; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2016 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2016 OWNER TO postgres;

--
-- Name: unioned_performance_data_2017; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2017 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2017 OWNER TO postgres;

--
-- Name: unioned_performance_data_2018; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2018 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2018 OWNER TO postgres;

--
-- Name: unioned_performance_data_2019; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2019 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2019 OWNER TO postgres;

--
-- Name: unioned_performance_data_2020; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2020 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2020 OWNER TO postgres;

--
-- Name: unioned_performance_data_2021; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2021 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2021 OWNER TO postgres;

--
-- Name: unioned_performance_data_2022; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2022 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2022 OWNER TO postgres;

--
-- Name: unioned_performance_data_2023; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2023 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2023 OWNER TO postgres;

--
-- Name: unioned_performance_data_2024; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2024 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2024 OWNER TO postgres;

--
-- Name: unioned_performance_data_2025; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.unioned_performance_data_2025 (
    horse_name character varying(132),
    age integer,
    horse_sex character varying(32),
    draw integer,
    headgear character varying(64),
    weight_carried character varying(16),
    weight_carried_lbs smallint,
    extra_weight smallint,
    jockey_claim smallint,
    finishing_position character varying(6),
    total_distance_beaten character varying(16),
    industry_sp character varying(16),
    betfair_win_sp numeric(6,2),
    betfair_place_sp numeric(6,2),
    price_change numeric(6,2),
    official_rating smallint,
    ts smallint,
    rpr smallint,
    tfr smallint,
    tfig smallint,
    in_play_high numeric(6,2),
    in_play_low numeric(6,2),
    in_race_comment text,
    tf_comment text,
    rp_comment text,
    tfr_view character varying(16),
    race_id integer,
    horse_id integer,
    jockey_id integer,
    trainer_id integer,
    owner_id integer,
    sire_id integer,
    dam_id integer,
    unique_id character varying(132),
    race_time timestamp without time zone,
    race_date date,
    race_title character varying(132),
    race_type character varying(32),
    race_class smallint,
    distance character varying(16),
    distance_yards numeric(10,2),
    distance_meters numeric(10,2),
    distance_kilometers numeric(10,2),
    conditions character varying(32),
    going character varying(32),
    number_of_runners smallint,
    hcap_range character varying(32),
    age_range character varying(32),
    surface character varying(32),
    total_prize_money integer,
    first_place_prize_money integer,
    winning_time character varying(32),
    time_seconds numeric(10,2),
    relative_time numeric(10,2),
    relative_to_standard character varying(16),
    country character varying(64),
    main_race_comment text,
    meeting_id character varying(132),
    course_id smallint,
    course character varying(132),
    dam character varying(132),
    sire character varying(132),
    trainer character varying(132),
    jockey character varying(132),
    data_type character varying(16),
    rating integer,
    speed_figure integer
);


ALTER TABLE public.unioned_performance_data_2025 OWNER TO postgres;

--
-- Name: comment_errors; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.comment_errors (
    horse_id text,
    horse_name text,
    analysis_link text,
    debug_link text,
    race_id text,
    race_date date,
    update_sql text
);


ALTER TABLE rp_raw.comment_errors OWNER TO postgres;

--
-- Name: missing_dates; Type: VIEW; Schema: rp_raw; Owner: postgres
--

CREATE VIEW rp_raw.missing_dates AS
 SELECT gs.date AS race_date
   FROM (generate_series((((now() - '1 year'::interval))::date)::timestamp without time zone, (((now() - '1 day'::interval))::date)::timestamp without time zone, '1 day'::interval) gs(date)
     LEFT JOIN ( SELECT DISTINCT results_links.race_date
           FROM rp_raw.results_links) distinct_dates ON ((gs.date = distinct_dates.race_date)))
  WHERE ((distinct_dates.race_date IS NULL) AND (NOT (gs.date = ANY (ARRAY[('2024-12-25'::date)::timestamp without time zone, ('2020-04-06'::date)::timestamp without time zone, ('2008-12-25'::date)::timestamp without time zone, ('2013-03-29'::date)::timestamp without time zone, ('2010-01-06'::date)::timestamp without time zone, ('2008-12-24'::date)::timestamp without time zone, ('2009-02-02'::date)::timestamp without time zone, ('2007-12-25'::date)::timestamp without time zone, ('2007-12-24'::date)::timestamp without time zone, ('2005-12-25'::date)::timestamp without time zone, ('2005-12-24'::date)::timestamp without time zone, ('2009-12-25'::date)::timestamp without time zone, ('2009-12-24'::date)::timestamp without time zone, ('2006-12-25'::date)::timestamp without time zone, ('2006-12-24'::date)::timestamp without time zone, ('2020-04-03'::date)::timestamp without time zone, ('2020-04-02'::date)::timestamp without time zone, ('2015-12-25'::date)::timestamp without time zone, ('2015-12-24'::date)::timestamp without time zone, ('2016-12-25'::date)::timestamp without time zone, ('2016-12-24'::date)::timestamp without time zone, ('2017-12-25'::date)::timestamp without time zone, ('2017-12-24'::date)::timestamp without time zone, ('2018-12-25'::date)::timestamp without time zone, ('2018-12-24'::date)::timestamp without time zone, ('2019-12-25'::date)::timestamp without time zone, ('2019-12-24'::date)::timestamp without time zone, ('2020-12-25'::date)::timestamp without time zone, ('2020-12-24'::date)::timestamp without time zone, ('2021-12-25'::date)::timestamp without time zone, ('2021-12-24'::date)::timestamp without time zone, ('2022-12-25'::date)::timestamp without time zone, ('2022-12-24'::date)::timestamp without time zone, ('2023-12-25'::date)::timestamp without time zone, ('2023-12-24'::date)::timestamp without time zone]))))
  ORDER BY gs.date DESC;


ALTER VIEW rp_raw.missing_dates OWNER TO postgres;

--
-- Name: results_errors; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.results_errors (
    link_url text
);


ALTER TABLE rp_raw.results_errors OWNER TO postgres;

--
-- Name: void_races; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.void_races (
    link_url text
);


ALTER TABLE rp_raw.void_races OWNER TO postgres;

--
-- Name: missing_results_links; Type: VIEW; Schema: rp_raw; Owner: postgres
--

CREATE VIEW rp_raw.missing_results_links AS
 SELECT rl.link_url
   FROM (rp_raw.results_links rl
     LEFT JOIN rp_raw.results_data rd ON ((rl.link_url = rd.debug_link)))
  WHERE ((rl.country_category = 1) AND (rd.debug_link IS NULL) AND (NOT (rl.link_url IN ( SELECT results_errors.link_url
           FROM rp_raw.results_errors))) AND (NOT (rl.link_url IN ( SELECT void_races.link_url
           FROM rp_raw.void_races))))
UNION
 SELECT DISTINCT rl.link_url
   FROM (rp_raw.results_links rl
     LEFT JOIN rp_raw.results_data rd ON ((rl.link_url = rd.debug_link)))
  WHERE ((rl.country_category = 1) AND (rl.race_date >= (CURRENT_DATE - '3 days'::interval)));


ALTER VIEW rp_raw.missing_results_links OWNER TO postgres;

--
-- Name: missing_results_links_world; Type: VIEW; Schema: rp_raw; Owner: postgres
--

CREATE VIEW rp_raw.missing_results_links_world AS
 SELECT rl.link_url
   FROM (rp_raw.results_links rl
     LEFT JOIN rp_raw.results_data_world rd ON ((rl.link_url = rd.debug_link)))
  WHERE ((rl.country_category = 2) AND (rd.debug_link IS NULL) AND (NOT (rl.link_url IN ( SELECT results_errors.link_url
           FROM rp_raw.results_errors))));


ALTER VIEW rp_raw.missing_results_links_world OWNER TO postgres;

--
-- Name: missing_todays_dates; Type: VIEW; Schema: rp_raw; Owner: postgres
--

CREATE VIEW rp_raw.missing_todays_dates AS
 WITH links AS (
         SELECT todays_links.link_url,
            todays_links.race_date,
            split_part(split_part(todays_links.link_url, '/'::text, 5), '/'::text, 1) AS course_id
           FROM rp_raw.todays_links
        )
 SELECT l.link_url
   FROM (links l
     LEFT JOIN entities.course ec ON ((l.course_id = (ec.rp_id)::text)))
  WHERE (((ec.country_id)::text = '1'::text) AND (l.race_date = CURRENT_DATE));


ALTER VIEW rp_raw.missing_todays_dates OWNER TO postgres;

--
-- Name: temp_comments; Type: TABLE; Schema: rp_raw; Owner: postgres
--

CREATE TABLE rp_raw.temp_comments (
    horse_id text,
    horse_name text,
    rp_comment text,
    race_id text,
    race_date date
);


ALTER TABLE rp_raw.temp_comments OWNER TO postgres;

--
-- Name: results_links; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.results_links (
    race_date date,
    link_url text,
    course_name text,
    country_category smallint,
    course_id text
);


ALTER TABLE tf_raw.results_links OWNER TO postgres;

--
-- Name: missing_dates; Type: VIEW; Schema: tf_raw; Owner: postgres
--

CREATE VIEW tf_raw.missing_dates AS
 SELECT gs.date AS race_date
   FROM (generate_series((((now() - '1 year'::interval))::date)::timestamp without time zone, (((now() - '1 day'::interval))::date)::timestamp without time zone, '1 day'::interval) gs(date)
     LEFT JOIN ( SELECT DISTINCT results_links.race_date
           FROM tf_raw.results_links) distinct_dates ON ((gs.date = distinct_dates.race_date)))
  WHERE ((distinct_dates.race_date IS NULL) AND (NOT (gs.date = ANY (ARRAY[('2005-03-25'::date)::timestamp without time zone, ('2009-12-23'::date)::timestamp without time zone, ('2020-04-06'::date)::timestamp without time zone, ('2008-12-25'::date)::timestamp without time zone, ('2013-03-29'::date)::timestamp without time zone, ('2010-01-06'::date)::timestamp without time zone, ('2008-12-24'::date)::timestamp without time zone, ('2009-02-02'::date)::timestamp without time zone, ('2007-12-25'::date)::timestamp without time zone, ('2007-12-24'::date)::timestamp without time zone, ('2005-12-25'::date)::timestamp without time zone, ('2005-12-24'::date)::timestamp without time zone, ('2009-12-25'::date)::timestamp without time zone, ('2009-12-24'::date)::timestamp without time zone, ('2006-12-25'::date)::timestamp without time zone, ('2006-12-24'::date)::timestamp without time zone, ('2020-04-03'::date)::timestamp without time zone, ('2020-04-02'::date)::timestamp without time zone, ('2015-12-25'::date)::timestamp without time zone, ('2015-12-24'::date)::timestamp without time zone, ('2016-12-25'::date)::timestamp without time zone, ('2016-12-24'::date)::timestamp without time zone, ('2017-12-25'::date)::timestamp without time zone, ('2017-12-24'::date)::timestamp without time zone, ('2018-12-25'::date)::timestamp without time zone, ('2018-12-24'::date)::timestamp without time zone, ('2019-12-25'::date)::timestamp without time zone, ('2019-12-24'::date)::timestamp without time zone, ('2020-12-25'::date)::timestamp without time zone, ('2020-12-24'::date)::timestamp without time zone, ('2021-12-25'::date)::timestamp without time zone, ('2021-12-24'::date)::timestamp without time zone, ('2022-12-25'::date)::timestamp without time zone, ('2022-12-24'::date)::timestamp without time zone, ('2023-12-25'::date)::timestamp without time zone, ('2023-12-24'::date)::timestamp without time zone]))))
  ORDER BY gs.date DESC;


ALTER VIEW tf_raw.missing_dates OWNER TO postgres;

--
-- Name: results_errors; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.results_errors (
    link_url text
);


ALTER TABLE tf_raw.results_errors OWNER TO postgres;

--
-- Name: missing_results_links; Type: VIEW; Schema: tf_raw; Owner: postgres
--

CREATE VIEW tf_raw.missing_results_links AS
 SELECT rl.link_url
   FROM (tf_raw.results_links rl
     LEFT JOIN tf_raw.results_data rd ON ((rl.link_url = rd.debug_link)))
  WHERE ((rl.country_category = 1) AND (rd.debug_link IS NULL) AND (NOT (rl.link_url IN ( SELECT results_errors.link_url
           FROM tf_raw.results_errors))))
UNION
 SELECT DISTINCT rl.link_url
   FROM (tf_raw.results_links rl
     LEFT JOIN tf_raw.results_data rd ON ((rl.link_url = rd.debug_link)))
  WHERE ((rl.country_category = 1) AND (rl.race_date >= (CURRENT_DATE - '3 days'::interval)))
UNION
 SELECT DISTINCT results_data.debug_link AS link_url
   FROM tf_raw.results_data
  WHERE ((results_data.main_race_comment = ''::text) AND (results_data.race_date > '2024-01-01'::date));


ALTER VIEW tf_raw.missing_results_links OWNER TO postgres;

--
-- Name: results_data_world; Type: TABLE; Schema: tf_raw; Owner: postgres
--

CREATE TABLE tf_raw.results_data_world (
    tf_rating character varying(64),
    tf_speed_figure character varying(64),
    draw character varying(64),
    trainer_name character varying(132),
    trainer_id character varying(32),
    jockey_name character varying(132),
    jockey_id character varying(32),
    sire_name character varying(132),
    sire_id character varying(32),
    dam_name character varying(132),
    dam_id character varying(32),
    finishing_position character varying(64),
    horse_name character varying(132),
    horse_id character varying(32),
    horse_name_link character varying(132),
    horse_age character varying(64),
    equipment character varying(64),
    official_rating character varying(64),
    fractional_price character varying(64),
    betfair_win_sp character varying(64),
    betfair_place_sp character varying(64),
    in_play_prices character varying(64),
    tf_comment text,
    course text,
    race_date date,
    race_time_debug character varying(32),
    race_time timestamp without time zone,
    course_id character varying(32),
    race text,
    race_id character varying(132),
    distance character varying(32),
    going character varying(64),
    prize character varying(64),
    hcap_range character varying(64),
    age_range character varying(64),
    race_type character varying(64),
    main_race_comment text,
    debug_link text,
    created_at timestamp without time zone,
    unique_id character varying(132)
);


ALTER TABLE tf_raw.results_data_world OWNER TO postgres;

--
-- Name: missing_results_links_world; Type: VIEW; Schema: tf_raw; Owner: postgres
--

CREATE VIEW tf_raw.missing_results_links_world AS
 WITH uk_ire_rp_data AS (
         SELECT DISTINCT rp_1.course,
            rp_1.course_id,
            rp_1.race_date
           FROM (rp_raw.results_data_world rp_1
             LEFT JOIN entities.horse eh ON (((rp_1.horse_id)::text = (eh.rp_id)::text)))
          WHERE ((eh.rp_id IS NOT NULL) AND (rp_1.race_date > '2015-01-01'::date))
          ORDER BY rp_1.course
        )
 SELECT rl.link_url
   FROM (((tf_raw.results_links rl
     LEFT JOIN tf_raw.results_data_world rd ON ((rl.link_url = rd.debug_link)))
     LEFT JOIN entities.course ec ON ((rl.course_id = (ec.tf_id)::text)))
     LEFT JOIN uk_ire_rp_data rp ON ((((ec.rp_id)::text = (rp.course_id)::text) AND (rl.race_date = rp.race_date))))
  WHERE ((rl.country_category = 2) AND (rd.debug_link IS NULL) AND (rp.race_date IS NOT NULL) AND (NOT (rl.link_url IN ( SELECT results_errors.link_url
           FROM tf_raw.results_errors))));


ALTER VIEW tf_raw.missing_results_links_world OWNER TO postgres;

--
-- Name: missing_todays_dates; Type: VIEW; Schema: tf_raw; Owner: postgres
--

CREATE VIEW tf_raw.missing_todays_dates AS
 WITH links AS (
         SELECT todays_links.link_url,
            todays_links.race_date,
            split_part(todays_links.link_url, '/'::text, 9) AS course_id
           FROM tf_raw.todays_links
        )
 SELECT l.link_url
   FROM (links l
     LEFT JOIN entities.course ec ON ((l.course_id = (ec.tf_id)::text)))
  WHERE (((ec.country_id)::text = '1'::text) AND (l.race_date = CURRENT_DATE));


ALTER VIEW tf_raw.missing_todays_dates OWNER TO postgres;

--
-- Name: unioned_performance_data_2010; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2010 FOR VALUES FROM ('2010-01-01') TO ('2011-01-01');


--
-- Name: unioned_performance_data_2011; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2011 FOR VALUES FROM ('2011-01-01') TO ('2012-01-01');


--
-- Name: unioned_performance_data_2012; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2012 FOR VALUES FROM ('2012-01-01') TO ('2013-01-01');


--
-- Name: unioned_performance_data_2013; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2013 FOR VALUES FROM ('2013-01-01') TO ('2014-01-01');


--
-- Name: unioned_performance_data_2014; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2014 FOR VALUES FROM ('2014-01-01') TO ('2015-01-01');


--
-- Name: unioned_performance_data_2015; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2015 FOR VALUES FROM ('2015-01-01') TO ('2016-01-01');


--
-- Name: unioned_performance_data_2016; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2016 FOR VALUES FROM ('2016-01-01') TO ('2017-01-01');


--
-- Name: unioned_performance_data_2017; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2017 FOR VALUES FROM ('2017-01-01') TO ('2018-01-01');


--
-- Name: unioned_performance_data_2018; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2018 FOR VALUES FROM ('2018-01-01') TO ('2019-01-01');


--
-- Name: unioned_performance_data_2019; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2019 FOR VALUES FROM ('2019-01-01') TO ('2020-01-01');


--
-- Name: unioned_performance_data_2020; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2020 FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');


--
-- Name: unioned_performance_data_2021; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2021 FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');


--
-- Name: unioned_performance_data_2022; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2022 FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');


--
-- Name: unioned_performance_data_2023; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2023 FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');


--
-- Name: unioned_performance_data_2024; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2024 FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');


--
-- Name: unioned_performance_data_2025; Type: TABLE ATTACH; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data ATTACH PARTITION public.unioned_performance_data_2025 FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');


--
-- Name: betting_session betting_session_pkey; Type: CONSTRAINT; Schema: api; Owner: postgres
--

ALTER TABLE ONLY api.betting_session
    ADD CONSTRAINT betting_session_pkey PRIMARY KEY (session_id);


--
-- Name: historical_selections historical_selections_unique_key; Type: CONSTRAINT; Schema: api; Owner: postgres
--

ALTER TABLE ONLY api.historical_selections
    ADD CONSTRAINT historical_selections_unique_key UNIQUE (race_date, market_id, selection_id);


--
-- Name: betting_selections_info unique_id_betting_type; Type: CONSTRAINT; Schema: api; Owner: postgres
--

ALTER TABLE ONLY api.betting_selections_info
    ADD CONSTRAINT unique_id_betting_type UNIQUE (unique_id, betting_type);


--
-- Name: results_data bf_raw_race_horse_id_unq; Type: CONSTRAINT; Schema: bf_raw; Owner: postgres
--

ALTER TABLE ONLY bf_raw.results_data
    ADD CONSTRAINT bf_raw_race_horse_id_unq UNIQUE (horse_id, race_id);


--
-- Name: results_data bf_unique_id_unq; Type: CONSTRAINT; Schema: bf_raw; Owner: postgres
--

ALTER TABLE ONLY bf_raw.results_data
    ADD CONSTRAINT bf_unique_id_unq UNIQUE (unique_id);


--
-- Name: today_horse todays_betfair_ids_horse_id_pd; Type: CONSTRAINT; Schema: bf_raw; Owner: postgres
--

ALTER TABLE ONLY bf_raw.today_horse
    ADD CONSTRAINT todays_betfair_ids_horse_id_pd UNIQUE (horse_id, bf_horse_id);


--
-- Name: dam dam_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.dam
    ADD CONSTRAINT dam_pkey PRIMARY KEY (id);


--
-- Name: horse horse_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.horse
    ADD CONSTRAINT horse_pkey PRIMARY KEY (id);


--
-- Name: jockey jockey_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.jockey
    ADD CONSTRAINT jockey_pkey PRIMARY KEY (id);


--
-- Name: owner owner_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.owner
    ADD CONSTRAINT owner_pkey PRIMARY KEY (id);


--
-- Name: owner rp_owner_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.owner
    ADD CONSTRAINT rp_owner_unique_id UNIQUE (rp_id, name);


--
-- Name: dam rp_tf_dam_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.dam
    ADD CONSTRAINT rp_tf_dam_unique_id UNIQUE (rp_id, tf_id);


--
-- Name: horse rp_tf_horse_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.horse
    ADD CONSTRAINT rp_tf_horse_unique_id UNIQUE (rp_id, tf_id);


--
-- Name: jockey rp_tf_jockey_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.jockey
    ADD CONSTRAINT rp_tf_jockey_unique_id UNIQUE (rp_id, tf_id);


--
-- Name: sire rp_tf_sire_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.sire
    ADD CONSTRAINT rp_tf_sire_unique_id UNIQUE (rp_id, tf_id);


--
-- Name: trainer rp_tf_trainer_unique_id; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.trainer
    ADD CONSTRAINT rp_tf_trainer_unique_id UNIQUE (rp_id, tf_id);


--
-- Name: sire sire_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.sire
    ADD CONSTRAINT sire_pkey PRIMARY KEY (id);


--
-- Name: trainer trainer_pkey; Type: CONSTRAINT; Schema: entities; Owner: postgres
--

ALTER TABLE ONLY entities.trainer
    ADD CONSTRAINT trainer_pkey PRIMARY KEY (id);


--
-- Name: race_results race_results_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.race_results
    ADD CONSTRAINT race_results_pkey PRIMARY KEY (unique_id);


--
-- Name: race_times race_times_pkey; Type: CONSTRAINT; Schema: live_betting; Owner: postgres
--

ALTER TABLE ONLY live_betting.race_times
    ADD CONSTRAINT race_times_pkey PRIMARY KEY (race_id);


--
-- Name: job_ids job_ids_pkey; Type: CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.job_ids
    ADD CONSTRAINT job_ids_pkey PRIMARY KEY (id);


--
-- Name: source_ids source_ids_pkey; Type: CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.source_ids
    ADD CONSTRAINT source_ids_pkey PRIMARY KEY (id);


--
-- Name: stage_ids stage_ids_pkey; Type: CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.stage_ids
    ADD CONSTRAINT stage_ids_pkey PRIMARY KEY (id);


--
-- Name: results_data results_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.results_data
    ADD CONSTRAINT results_data_pkey PRIMARY KEY (unique_id);


--
-- Name: todays_data todays_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.todays_data
    ADD CONSTRAINT todays_data_pkey PRIMARY KEY (unique_id);


--
-- Name: unioned_results_data unioned_unq_id_cns; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_results_data
    ADD CONSTRAINT unioned_unq_id_cns UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2010 unioned_performance_data_2010_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2010
    ADD CONSTRAINT unioned_performance_data_2010_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2011 unioned_performance_data_2011_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2011
    ADD CONSTRAINT unioned_performance_data_2011_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2012 unioned_performance_data_2012_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2012
    ADD CONSTRAINT unioned_performance_data_2012_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2013 unioned_performance_data_2013_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2013
    ADD CONSTRAINT unioned_performance_data_2013_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2014 unioned_performance_data_2014_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2014
    ADD CONSTRAINT unioned_performance_data_2014_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2015 unioned_performance_data_2015_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2015
    ADD CONSTRAINT unioned_performance_data_2015_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2016 unioned_performance_data_2016_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2016
    ADD CONSTRAINT unioned_performance_data_2016_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2017 unioned_performance_data_2017_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2017
    ADD CONSTRAINT unioned_performance_data_2017_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2018 unioned_performance_data_2018_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2018
    ADD CONSTRAINT unioned_performance_data_2018_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2019 unioned_performance_data_2019_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2019
    ADD CONSTRAINT unioned_performance_data_2019_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2020 unioned_performance_data_2020_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2020
    ADD CONSTRAINT unioned_performance_data_2020_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2021 unioned_performance_data_2021_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2021
    ADD CONSTRAINT unioned_performance_data_2021_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2022 unioned_performance_data_2022_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2022
    ADD CONSTRAINT unioned_performance_data_2022_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2023 unioned_performance_data_2023_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2023
    ADD CONSTRAINT unioned_performance_data_2023_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2024 unioned_performance_data_2024_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2024
    ADD CONSTRAINT unioned_performance_data_2024_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: unioned_performance_data_2025 unioned_performance_data_2025_unique_id_race_date_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.unioned_performance_data_2025
    ADD CONSTRAINT unioned_performance_data_2025_unique_id_race_date_key UNIQUE (unique_id, race_date);


--
-- Name: results_data_world rp_raw_npd_unq_id; Type: CONSTRAINT; Schema: rp_raw; Owner: postgres
--

ALTER TABLE ONLY rp_raw.results_data_world
    ADD CONSTRAINT rp_raw_npd_unq_id UNIQUE (unique_id);


--
-- Name: results_data rp_raw_pd_unq_id; Type: CONSTRAINT; Schema: rp_raw; Owner: postgres
--

ALTER TABLE ONLY rp_raw.results_data
    ADD CONSTRAINT rp_raw_pd_unq_id UNIQUE (unique_id);


--
-- Name: results_data_world tf_raw_npd_unq_id; Type: CONSTRAINT; Schema: tf_raw; Owner: postgres
--

ALTER TABLE ONLY tf_raw.results_data_world
    ADD CONSTRAINT tf_raw_npd_unq_id UNIQUE (unique_id);


--
-- Name: results_data tf_raw_pd_unq_id; Type: CONSTRAINT; Schema: tf_raw; Owner: postgres
--

ALTER TABLE ONLY tf_raw.results_data
    ADD CONSTRAINT tf_raw_pd_unq_id UNIQUE (unique_id);


--
-- Name: idx_betting_session_active; Type: INDEX; Schema: api; Owner: postgres
--

CREATE INDEX idx_betting_session_active ON api.betting_session USING btree (is_active);


--
-- Name: idx_historical_selections_race_date; Type: INDEX; Schema: api; Owner: postgres
--

CREATE INDEX idx_historical_selections_race_date ON api.historical_selections USING btree (race_date);


--
-- Name: idx_historical_selections_unique; Type: INDEX; Schema: api; Owner: postgres
--

CREATE INDEX idx_historical_selections_unique ON api.historical_selections USING btree (race_date, market_id, selection_id);


--
-- Name: idx_dam_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_dam_id ON entities.dam USING btree (rp_id);


--
-- Name: idx_dam_name; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_dam_name ON entities.dam USING btree (name);


--
-- Name: idx_horse_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_horse_id ON entities.horse USING btree (rp_id);


--
-- Name: idx_horse_name; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_horse_name ON entities.horse USING btree (name);


--
-- Name: idx_jockey_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_jockey_id ON entities.jockey USING btree (rp_id);


--
-- Name: idx_jockey_name; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_jockey_name ON entities.jockey USING btree (name);


--
-- Name: idx_sire_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_sire_id ON entities.sire USING btree (rp_id);


--
-- Name: idx_sire_name; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_sire_name ON entities.sire USING btree (name);


--
-- Name: idx_tf_dam_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_tf_dam_id ON entities.dam USING btree (tf_id);


--
-- Name: idx_tf_horse_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_tf_horse_id ON entities.horse USING btree (tf_id);


--
-- Name: idx_tf_jockey_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_tf_jockey_id ON entities.jockey USING btree (tf_id);


--
-- Name: idx_tf_sire_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_tf_sire_id ON entities.sire USING btree (tf_id);


--
-- Name: idx_tf_trainer_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_tf_trainer_id ON entities.trainer USING btree (tf_id);


--
-- Name: idx_trainer_id; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_trainer_id ON entities.trainer USING btree (rp_id);


--
-- Name: idx_trainer_name; Type: INDEX; Schema: entities; Owner: postgres
--

CREATE INDEX idx_trainer_name ON entities.trainer USING btree (name);


--
-- Name: idx_horse_id_upd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_horse_id_upd ON ONLY public.unioned_results_data USING btree (horse_id);


--
-- Name: idx_race_date_upd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_race_date_upd ON ONLY public.unioned_results_data USING btree (race_date);


--
-- Name: idx_race_id_upd; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_race_id_upd ON ONLY public.unioned_results_data USING btree (race_id);


--
-- Name: idx_unique_id_rp_comment_public; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_unique_id_rp_comment_public ON public.results_data USING btree (unique_id, rp_comment);


--
-- Name: unioned_performance_data_2010_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2010_horse_id_idx ON public.unioned_performance_data_2010 USING btree (horse_id);


--
-- Name: unioned_performance_data_2010_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2010_race_date_idx ON public.unioned_performance_data_2010 USING btree (race_date);


--
-- Name: unioned_performance_data_2010_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2010_race_id_idx ON public.unioned_performance_data_2010 USING btree (race_id);


--
-- Name: unioned_performance_data_2011_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2011_horse_id_idx ON public.unioned_performance_data_2011 USING btree (horse_id);


--
-- Name: unioned_performance_data_2011_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2011_race_date_idx ON public.unioned_performance_data_2011 USING btree (race_date);


--
-- Name: unioned_performance_data_2011_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2011_race_id_idx ON public.unioned_performance_data_2011 USING btree (race_id);


--
-- Name: unioned_performance_data_2012_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2012_horse_id_idx ON public.unioned_performance_data_2012 USING btree (horse_id);


--
-- Name: unioned_performance_data_2012_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2012_race_date_idx ON public.unioned_performance_data_2012 USING btree (race_date);


--
-- Name: unioned_performance_data_2012_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2012_race_id_idx ON public.unioned_performance_data_2012 USING btree (race_id);


--
-- Name: unioned_performance_data_2013_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2013_horse_id_idx ON public.unioned_performance_data_2013 USING btree (horse_id);


--
-- Name: unioned_performance_data_2013_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2013_race_date_idx ON public.unioned_performance_data_2013 USING btree (race_date);


--
-- Name: unioned_performance_data_2013_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2013_race_id_idx ON public.unioned_performance_data_2013 USING btree (race_id);


--
-- Name: unioned_performance_data_2014_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2014_horse_id_idx ON public.unioned_performance_data_2014 USING btree (horse_id);


--
-- Name: unioned_performance_data_2014_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2014_race_date_idx ON public.unioned_performance_data_2014 USING btree (race_date);


--
-- Name: unioned_performance_data_2014_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2014_race_id_idx ON public.unioned_performance_data_2014 USING btree (race_id);


--
-- Name: unioned_performance_data_2015_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2015_horse_id_idx ON public.unioned_performance_data_2015 USING btree (horse_id);


--
-- Name: unioned_performance_data_2015_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2015_race_date_idx ON public.unioned_performance_data_2015 USING btree (race_date);


--
-- Name: unioned_performance_data_2015_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2015_race_id_idx ON public.unioned_performance_data_2015 USING btree (race_id);


--
-- Name: unioned_performance_data_2016_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2016_horse_id_idx ON public.unioned_performance_data_2016 USING btree (horse_id);


--
-- Name: unioned_performance_data_2016_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2016_race_date_idx ON public.unioned_performance_data_2016 USING btree (race_date);


--
-- Name: unioned_performance_data_2016_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2016_race_id_idx ON public.unioned_performance_data_2016 USING btree (race_id);


--
-- Name: unioned_performance_data_2017_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2017_horse_id_idx ON public.unioned_performance_data_2017 USING btree (horse_id);


--
-- Name: unioned_performance_data_2017_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2017_race_date_idx ON public.unioned_performance_data_2017 USING btree (race_date);


--
-- Name: unioned_performance_data_2017_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2017_race_id_idx ON public.unioned_performance_data_2017 USING btree (race_id);


--
-- Name: unioned_performance_data_2018_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2018_horse_id_idx ON public.unioned_performance_data_2018 USING btree (horse_id);


--
-- Name: unioned_performance_data_2018_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2018_race_date_idx ON public.unioned_performance_data_2018 USING btree (race_date);


--
-- Name: unioned_performance_data_2018_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2018_race_id_idx ON public.unioned_performance_data_2018 USING btree (race_id);


--
-- Name: unioned_performance_data_2019_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2019_horse_id_idx ON public.unioned_performance_data_2019 USING btree (horse_id);


--
-- Name: unioned_performance_data_2019_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2019_race_date_idx ON public.unioned_performance_data_2019 USING btree (race_date);


--
-- Name: unioned_performance_data_2019_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2019_race_id_idx ON public.unioned_performance_data_2019 USING btree (race_id);


--
-- Name: unioned_performance_data_2020_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2020_horse_id_idx ON public.unioned_performance_data_2020 USING btree (horse_id);


--
-- Name: unioned_performance_data_2020_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2020_race_date_idx ON public.unioned_performance_data_2020 USING btree (race_date);


--
-- Name: unioned_performance_data_2020_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2020_race_id_idx ON public.unioned_performance_data_2020 USING btree (race_id);


--
-- Name: unioned_performance_data_2021_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2021_horse_id_idx ON public.unioned_performance_data_2021 USING btree (horse_id);


--
-- Name: unioned_performance_data_2021_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2021_race_date_idx ON public.unioned_performance_data_2021 USING btree (race_date);


--
-- Name: unioned_performance_data_2021_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2021_race_id_idx ON public.unioned_performance_data_2021 USING btree (race_id);


--
-- Name: unioned_performance_data_2022_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2022_horse_id_idx ON public.unioned_performance_data_2022 USING btree (horse_id);


--
-- Name: unioned_performance_data_2022_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2022_race_date_idx ON public.unioned_performance_data_2022 USING btree (race_date);


--
-- Name: unioned_performance_data_2022_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2022_race_id_idx ON public.unioned_performance_data_2022 USING btree (race_id);


--
-- Name: unioned_performance_data_2023_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2023_horse_id_idx ON public.unioned_performance_data_2023 USING btree (horse_id);


--
-- Name: unioned_performance_data_2023_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2023_race_date_idx ON public.unioned_performance_data_2023 USING btree (race_date);


--
-- Name: unioned_performance_data_2023_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2023_race_id_idx ON public.unioned_performance_data_2023 USING btree (race_id);


--
-- Name: unioned_performance_data_2024_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2024_horse_id_idx ON public.unioned_performance_data_2024 USING btree (horse_id);


--
-- Name: unioned_performance_data_2024_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2024_race_date_idx ON public.unioned_performance_data_2024 USING btree (race_date);


--
-- Name: unioned_performance_data_2024_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2024_race_id_idx ON public.unioned_performance_data_2024 USING btree (race_id);


--
-- Name: unioned_performance_data_2025_horse_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2025_horse_id_idx ON public.unioned_performance_data_2025 USING btree (horse_id);


--
-- Name: unioned_performance_data_2025_race_date_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2025_race_date_idx ON public.unioned_performance_data_2025 USING btree (race_date);


--
-- Name: unioned_performance_data_2025_race_id_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX unioned_performance_data_2025_race_id_idx ON public.unioned_performance_data_2025 USING btree (race_id);


--
-- Name: idx_days_results_links_errors_link_url; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_days_results_links_errors_link_url ON rp_raw.results_errors USING btree (link_url);


--
-- Name: idx_rp_raw_results_data_debug_link; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_debug_link ON rp_raw.results_data USING btree (debug_link);


--
-- Name: idx_rp_raw_results_data_horse_id; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_horse_id ON rp_raw.results_data USING btree (horse_id);


--
-- Name: idx_rp_raw_results_data_race_date; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_race_date ON rp_raw.results_data USING btree (race_date);


--
-- Name: idx_rp_raw_results_data_race_date_course_id; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_race_date_course_id ON rp_raw.results_data USING btree (race_date, course_id);


--
-- Name: idx_rp_raw_results_data_race_date_debug_link; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_race_date_debug_link ON rp_raw.results_data USING btree (race_date, debug_link);


--
-- Name: idx_rp_raw_results_data_unique_id; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_unique_id ON rp_raw.results_data USING btree (unique_id);


--
-- Name: idx_rp_raw_results_data_wd_debug_link; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_wd_debug_link ON rp_raw.results_data_world USING btree (debug_link);


--
-- Name: idx_rp_raw_results_data_wd_horse_id; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_wd_horse_id ON rp_raw.results_data_world USING btree (horse_id);


--
-- Name: idx_rp_raw_results_data_wd_race_date; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_wd_race_date ON rp_raw.results_data_world USING btree (race_date);


--
-- Name: idx_rp_raw_results_data_wd_unique_id; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_rp_raw_results_data_wd_unique_id ON rp_raw.results_data_world USING btree (unique_id);


--
-- Name: idx_unique_id_rp_comment_raw; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX idx_unique_id_rp_comment_raw ON rp_raw.results_data USING btree (unique_id, rp_comment);


--
-- Name: rp_idx_results_links_country_category; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX rp_idx_results_links_country_category ON rp_raw.results_links USING btree (country_category);


--
-- Name: rp_idx_results_links_link_url; Type: INDEX; Schema: rp_raw; Owner: postgres
--

CREATE INDEX rp_idx_results_links_link_url ON rp_raw.results_links USING btree (link_url);


--
-- Name: idx_days_results_links_errors_link_url; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_days_results_links_errors_link_url ON tf_raw.results_errors USING btree (link_url);


--
-- Name: idx_tf_raw_performance_data_debug_link; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_debug_link ON tf_raw.results_data USING btree (debug_link);


--
-- Name: idx_tf_raw_performance_data_horse_id; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_horse_id ON tf_raw.results_data USING btree (horse_id);


--
-- Name: idx_tf_raw_performance_data_race_date; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_race_date ON tf_raw.results_data USING btree (race_date);


--
-- Name: idx_tf_raw_performance_data_race_date_course_id; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_race_date_course_id ON tf_raw.results_data USING btree (race_date, course_id);


--
-- Name: idx_tf_raw_performance_data_race_date_debug_link; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_race_date_debug_link ON tf_raw.results_data USING btree (race_date, debug_link);


--
-- Name: idx_tf_raw_performance_data_wd_debug_link; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_wd_debug_link ON tf_raw.results_data_world USING btree (debug_link);


--
-- Name: idx_tf_raw_performance_data_wd_horse_id; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_wd_horse_id ON tf_raw.results_data_world USING btree (horse_id);


--
-- Name: idx_tf_raw_performance_data_wd_race_date; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX idx_tf_raw_performance_data_wd_race_date ON tf_raw.results_data_world USING btree (race_date);


--
-- Name: tf_idx_results_links_country_category; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX tf_idx_results_links_country_category ON tf_raw.results_links USING btree (country_category);


--
-- Name: tf_idx_results_links_link_url; Type: INDEX; Schema: tf_raw; Owner: postgres
--

CREATE INDEX tf_idx_results_links_link_url ON tf_raw.results_links USING btree (link_url);


--
-- Name: unioned_performance_data_2010_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2010_horse_id_idx;


--
-- Name: unioned_performance_data_2010_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2010_race_date_idx;


--
-- Name: unioned_performance_data_2010_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2010_race_id_idx;


--
-- Name: unioned_performance_data_2010_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2010_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2011_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2011_horse_id_idx;


--
-- Name: unioned_performance_data_2011_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2011_race_date_idx;


--
-- Name: unioned_performance_data_2011_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2011_race_id_idx;


--
-- Name: unioned_performance_data_2011_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2011_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2012_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2012_horse_id_idx;


--
-- Name: unioned_performance_data_2012_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2012_race_date_idx;


--
-- Name: unioned_performance_data_2012_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2012_race_id_idx;


--
-- Name: unioned_performance_data_2012_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2012_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2013_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2013_horse_id_idx;


--
-- Name: unioned_performance_data_2013_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2013_race_date_idx;


--
-- Name: unioned_performance_data_2013_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2013_race_id_idx;


--
-- Name: unioned_performance_data_2013_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2013_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2014_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2014_horse_id_idx;


--
-- Name: unioned_performance_data_2014_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2014_race_date_idx;


--
-- Name: unioned_performance_data_2014_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2014_race_id_idx;


--
-- Name: unioned_performance_data_2014_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2014_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2015_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2015_horse_id_idx;


--
-- Name: unioned_performance_data_2015_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2015_race_date_idx;


--
-- Name: unioned_performance_data_2015_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2015_race_id_idx;


--
-- Name: unioned_performance_data_2015_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2015_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2016_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2016_horse_id_idx;


--
-- Name: unioned_performance_data_2016_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2016_race_date_idx;


--
-- Name: unioned_performance_data_2016_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2016_race_id_idx;


--
-- Name: unioned_performance_data_2016_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2016_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2017_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2017_horse_id_idx;


--
-- Name: unioned_performance_data_2017_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2017_race_date_idx;


--
-- Name: unioned_performance_data_2017_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2017_race_id_idx;


--
-- Name: unioned_performance_data_2017_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2017_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2018_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2018_horse_id_idx;


--
-- Name: unioned_performance_data_2018_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2018_race_date_idx;


--
-- Name: unioned_performance_data_2018_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2018_race_id_idx;


--
-- Name: unioned_performance_data_2018_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2018_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2019_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2019_horse_id_idx;


--
-- Name: unioned_performance_data_2019_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2019_race_date_idx;


--
-- Name: unioned_performance_data_2019_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2019_race_id_idx;


--
-- Name: unioned_performance_data_2019_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2019_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2020_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2020_horse_id_idx;


--
-- Name: unioned_performance_data_2020_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2020_race_date_idx;


--
-- Name: unioned_performance_data_2020_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2020_race_id_idx;


--
-- Name: unioned_performance_data_2020_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2020_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2021_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2021_horse_id_idx;


--
-- Name: unioned_performance_data_2021_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2021_race_date_idx;


--
-- Name: unioned_performance_data_2021_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2021_race_id_idx;


--
-- Name: unioned_performance_data_2021_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2021_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2022_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2022_horse_id_idx;


--
-- Name: unioned_performance_data_2022_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2022_race_date_idx;


--
-- Name: unioned_performance_data_2022_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2022_race_id_idx;


--
-- Name: unioned_performance_data_2022_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2022_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2023_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2023_horse_id_idx;


--
-- Name: unioned_performance_data_2023_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2023_race_date_idx;


--
-- Name: unioned_performance_data_2023_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2023_race_id_idx;


--
-- Name: unioned_performance_data_2023_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2023_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2024_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2024_horse_id_idx;


--
-- Name: unioned_performance_data_2024_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2024_race_date_idx;


--
-- Name: unioned_performance_data_2024_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2024_race_id_idx;


--
-- Name: unioned_performance_data_2024_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2024_unique_id_race_date_key;


--
-- Name: unioned_performance_data_2025_horse_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_horse_id_upd ATTACH PARTITION public.unioned_performance_data_2025_horse_id_idx;


--
-- Name: unioned_performance_data_2025_race_date_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_date_upd ATTACH PARTITION public.unioned_performance_data_2025_race_date_idx;


--
-- Name: unioned_performance_data_2025_race_id_idx; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.idx_race_id_upd ATTACH PARTITION public.unioned_performance_data_2025_race_id_idx;


--
-- Name: unioned_performance_data_2025_unique_id_race_date_key; Type: INDEX ATTACH; Schema: public; Owner: postgres
--

ALTER INDEX public.unioned_unq_id_cns ATTACH PARTITION public.unioned_performance_data_2025_unique_id_race_date_key;


--
-- Name: job_ids job_ids_stage_id_fkey; Type: FK CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.job_ids
    ADD CONSTRAINT job_ids_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES monitoring.stage_ids(id);


--
-- Name: pipeline_status pipeline_status_job_id_fkey; Type: FK CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.pipeline_status
    ADD CONSTRAINT pipeline_status_job_id_fkey FOREIGN KEY (job_id) REFERENCES monitoring.job_ids(id);


--
-- Name: pipeline_status pipeline_status_source_id_fkey; Type: FK CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.pipeline_status
    ADD CONSTRAINT pipeline_status_source_id_fkey FOREIGN KEY (source_id) REFERENCES monitoring.source_ids(id);


--
-- Name: pipeline_status pipeline_status_stage_id_fkey; Type: FK CONSTRAINT; Schema: monitoring; Owner: postgres
--

ALTER TABLE ONLY monitoring.pipeline_status
    ADD CONSTRAINT pipeline_status_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES monitoring.stage_ids(id);


--
-- PostgreSQL database dump complete
--

