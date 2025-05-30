import argparse

from api_helpers.clients import get_betfair_client
from api_helpers.config import config
from api_helpers.helpers.logging_config import I, W
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..llm_models.chat_models import ChatModels
from ..raw.betfair.ingestor import BFIngestor
from ..raw.racing_post.ingestor import RPIngestor
from ..raw.timeform.ingestor import TFIngestor


def run_ingestion_pipeline(
    storage_client: IStorageClient, pipeline_args: argparse.Namespace | None = None
):
    I(f"Running ingestion pipeline with args: {pipeline_args}")
    betfair_client = get_betfair_client()
    chat_model = ChatModels(model_name="google")

    rp_ingestor = RPIngestor(
        config=config, storage_client=storage_client, chat_model=chat_model
    )
    tf_ingestor = TFIngestor(config=config, storage_client=storage_client)
    bf_ingestor = BFIngestor(
        config=config, storage_client=storage_client, betfair_client=betfair_client
    )

    rp_ingestor.ingest_results_links()
    tf_ingestor.ingest_results_links()

    rp_ingestor.ingest_todays_links()
    tf_ingestor.ingest_todays_links()

    rp_ingestor.ingest_todays_data()
    tf_ingestor.ingest_todays_data()

    rp_ingestor.ingest_results_data()
    tf_ingestor.ingest_results_data()

    rp_ingestor.ingest_results_data_world()
    tf_ingestor.ingest_results_data_world()

    bf_ingestor.ingest_todays_data()
    bf_ingestor.ingest_historical_data()

    if pipeline_args.comments:
        I("Condition met: --comments flag was used.")
        rp_ingestor.ingest_results_comments()
    else:
        W("Skipping comments processing: --comments flag was NOT used.")

    if pipeline_args.world_comments:
        I("Condition met: --world-comments flag was used.")
        rp_ingestor.ingest_results_comments_world()
    else:
        W("Skipping world comments processing: --world-comments flag was NOT used.")
