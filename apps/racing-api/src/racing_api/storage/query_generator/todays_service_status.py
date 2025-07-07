class ServiceStatusSQLGenerator:
    @staticmethod
    def define_todays_service_status_sql():
        return "SELECT * FROM monitoring.service_job_run_times"

    @staticmethod
    def get_todays_service_status_sql():
        return ServiceStatusSQLGenerator.define_todays_service_status_sql()
