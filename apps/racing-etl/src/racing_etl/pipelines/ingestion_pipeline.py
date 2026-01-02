from datetime import datetime

from api_helpers.clients import get_betfair_client
from api_helpers.config import config
from api_helpers.interfaces.storage_client_interface import IStorageClient

from ..llm_models.chat_models import ChatModels
from ..raw.betfair.ingestor import BFIngestor
from ..raw.racing_post.ingestor import RPIngestor
from ..raw.timeform.ingestor import TFIngestor


def run_ingestion_pipeline(storage_client: IStorageClient):
    chat_model = ChatModels(model_name="google")

    # Racing Post scraping
    with RPIngestor(
        config=config,
        storage_client=storage_client,
        chat_model=chat_model,
        headless=True,
    ) as rp_ingestor:
        # if later than 1pm skip todays
        current_hour = datetime.now().hour
        if current_hour < 12:
            rp_ingestor.ingest_todays_links()
            rp_ingestor.ingest_todays_data()
        rp_ingestor.ingest_results_links()
        rp_ingestor.ingest_results_data()

        # Only ingest world results on Sundays
        if datetime.now().weekday() == 6:
            rp_ingestor.ingest_results_data_world()

    # Timeform scraping (browser closed above, can start fresh)
    with TFIngestor(
        config=config, storage_client=storage_client, headless=True
    ) as tf_ingestor:
        if current_hour < 12:
            tf_ingestor.ingest_todays_links()
            tf_ingestor.ingest_todays_data()
        tf_ingestor.ingest_results_links()
        tf_ingestor.ingest_results_data()

        # Only ingest world results on Sundays
        if datetime.now().weekday() == 6:
            tf_ingestor.ingest_results_data_world()

    # Betfair data (no browser needed)
    betfair_client = get_betfair_client()
    bf_ingestor = BFIngestor(
        config=config, storage_client=storage_client, betfair_client=betfair_client
    )
    bf_ingestor.ingest_todays_data()
