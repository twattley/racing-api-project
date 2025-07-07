class PipelineStatusSQLGenerator:
    @staticmethod
    def define_todays_pipeline_status_sql():
        return f"""
            WITH ranked_jobs AS (
                SELECT 
                    j.id as job_id, 
                    st.id as stage_id, 
                    st.name as stage_name,
                    j.name as job_name, 
                    sc.id as source_id,
                    sc.name as source_name,
                    s.warnings,
                    s.errors,
                    s.success_indicator,
                    s.date_processed,
                    ROW_NUMBER() OVER (
                        PARTITION BY j.id, sc.id, st.id 
                        ORDER BY s.date_processed DESC
                    ) as rn
                FROM monitoring.job_ids j
                LEFT JOIN monitoring.pipeline_status s ON j.id = s.job_id
                LEFT JOIN monitoring.source_ids sc ON sc.id = s.source_id
                LEFT JOIN monitoring.stage_ids st ON st.id = s.stage_id
                WHERE s.success_indicator = true
            )
            SELECT 	job_id, 
                    stage_id, 
                    stage_name,
                    job_name, 
                    source_id,
                    source_name,
                    warnings,
                    errors,
                    success_indicator,
                    date_processed 
                FROM ranked_jobs WHERE rn = 1
            ORDER BY job_id, source_id, stage_id;
            """

    @staticmethod
    def define_todays_pipeline_status_errors_sql():
        return f"""
            WITH ranked_jobs AS (
                SELECT 
                    j.id as job_id, 
                    st.id as stage_id, 
                    st.name as stage_name,
                    j.name as job_name, 
                    sc.id as source_id,
                    sc.name as source_name,
                    s.warnings,
                    s.errors,
                    s.success_indicator,
                    s.date_processed,
                    ROW_NUMBER() OVER (
                        PARTITION BY j.id, sc.id, st.id 
                        ORDER BY s.date_processed DESC
                    ) as rn
                FROM monitoring.job_ids j
                LEFT JOIN monitoring.pipeline_status s ON j.id = s.job_id
                LEFT JOIN monitoring.source_ids sc ON sc.id = s.source_id
                LEFT JOIN monitoring.stage_ids st ON st.id = s.stage_id
                WHERE s.success_indicator = true
            )
            SELECT 
                rj.job_id, 
                rj.stage_id, 
                rj.stage_name,
                rj.job_name, 
                rj.source_id,
                rj.source_name,
                rj.warnings,
                rj.errors,
                rj.success_indicator,
                rj.date_processed,
                pl.log_level,
                pl.message
            FROM ranked_jobs rj
            LEFT JOIN monitoring.pipeline_logs pl 
                ON pl.job_id = rj.job_id
                AND pl.source_id = rj.source_id
                AND pl.stage_id = rj.stage_id
                AND pl.date_processed = rj.date_processed
            WHERE rj.rn = 1
            AND pl.log_level IN ('WARNING', 'ERROR')
            ORDER BY rj.job_id, rj.source_id, rj.stage_id;


            """

    @staticmethod
    def get_todays_pipeline_status_sql():
        return PipelineStatusSQLGenerator.define_todays_pipeline_status_sql()
