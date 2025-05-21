Horse type looks to have become unavailable in RP results from Oct 1st ish

create view entities.missing_rp_entities as
SELECT r.race_timestamp,
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
r.course_id,
r.unique_id,
ec._,
eh._
FROM rp_raw.results_data r
LEFT JOIN results_data pr ON r.unique_id::text = pr.unique_id::text
LEFT JOIN entities.course ec ON r.course_id = ec.rp_id
LEFT JOIN entities.horse eh ON r.horse_id = eh.rp_id
LEFT JOIN tf_raw.results_data tf
ON tf.course_id = ec.tf_id
AND tf.horse_id = eh.tf_id
AND tf.race_date = r.race_date
WHERE pr.unique_id IS NULL
AND r.unique_id IS NOT NULL
AND eh.rp_id IS NULL
