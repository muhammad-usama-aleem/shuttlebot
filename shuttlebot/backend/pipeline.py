import time
import uuid
from datetime import date, timedelta
from typing import List

from loguru import logger as logging
from rich import print
from sqlmodel import Session

from shuttlebot.backend.database import (
    PipelineRefreshStatus,
    SportScanner,
    delete_and_insert_slots_to_database,
    engine,
    get_refresh_status_for_pipeline,
    initialize_db_and_tables,
    pipeline_refresh_decision_based_on_interval,
    update_refresh_status_for_pipeline,
)
from shuttlebot.backend.parsers.better import api as BetterOrganisation
from shuttlebot.backend.parsers.citysports import api as CitySports
from shuttlebot.backend.utils import (
    find_consecutive_slots,
    format_consecutive_slots_groupings,
    timeit,
)


def pipeline_data_refresh():
    update_refresh_status_for_pipeline(engine, PipelineRefreshStatus.RUNNING)
    today = date.today()
    dates = [today + timedelta(days=i) for i in range(6)]
    logging.info(f"Finding slots for dates: {dates}")

    logging.debug(
        f"Fetching data for org: 'better.org.uk' - dates: "
        f"`{dates[0]}` to {dates[-1]}"
    )
    slots_fetched_org_hash_817c4e0f86723d52f14291327ca1723dc00a8615 = (
        BetterOrganisation.pipeline(dates)
    )
    logging.info(
        "Delete/Insert slots for org: 817c4e0f86723d52f14291327ca1723dc00a8615"
    )
    delete_and_insert_slots_to_database(
        slots_fetched_org_hash_817c4e0f86723d52f14291327ca1723dc00a8615,
        organisation="better.org.uk",
    )

    dates = [today + timedelta(days=i) for i in range(30)]
    logging.debug(
        f"Fetching data for org: 'citysport.org.uk' - dates: "
        f"`{dates[0]}` to {dates[-1]}"
    )
    slots_fetched_org_hash_378b041c5cd6e6844e173b295b62f259f78189b1 = (
        CitySports.pipeline(dates)
    )
    logging.info(
        "Delete/Insert slots for org: 378b041c5cd6e6844e173b295b62f259f78189b1"
    )
    delete_and_insert_slots_to_database(
        slots_fetched_org_hash_378b041c5cd6e6844e173b295b62f259f78189b1,
        organisation="citysport.org.uk",
    )

    update_refresh_status_for_pipeline(engine, PipelineRefreshStatus.COMPLETED)


@timeit
def main():
    """Gathers data from all sources/providers and loads to SQL database"""
    pipeline_data_refresh()


if __name__ == "__main__":
    main()
