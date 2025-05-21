from api_helpers.helpers.processing_utils import pt
from api_helpers.helpers.logging_config import I
from api_helpers.interfaces.storage_client_interface import IStorageClient


def run_data_checks_pipeline(storage_client: IStorageClient):
    I("Running data checks pipeline")
    pt(
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_dams;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_horses;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_jockeys;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_owners;"
        ),
    )
    pt(
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_sires;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_trainers;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_results_data;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_todays_data;"
        ),
    )
    pt(
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_results_links;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_todays_links;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.missing_todays_betfair_horse_ids;"
        ),
    )

    pt(
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.raw_ingestion_counts;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.raw_todays_ingestion_counts;"
        ),
        lambda: storage_client.execute_query(
            "REFRESH MATERIALIZED VIEW data_quality.todays_processed_links_counts;"
        ),
    )
