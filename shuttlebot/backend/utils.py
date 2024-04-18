import itertools
import sys
from datetime import date, datetime, time, timedelta
from time import time as timer
from typing import Dict, List, Optional
from functools import wraps

import pandas as pd
from loguru import logger as logging
from pydantic import BaseModel, ValidationError
from shuttlebot.backend.database import engine, SportScanner, get_all_rows, SportsVenue
from sqlmodel import select

from rich import print
from shuttlebot import config


def timeit(func):
    """Calculates the execution time of the function on top of which the decorator is assigned"""

    @wraps(func)
    def wrap_func(*args, **kwargs):
        tic = timer()
        result = func(*args, **kwargs)
        tac = timer()
        logging.info(f"Function {func.__name__!r} executed in {(tac - tic):.4f}s")
        return result

    return wrap_func


class ConsecutiveSlotsCarousalDisplay(BaseModel):
    """Model to store information displayed via Card carousal"""
    distance: str
    venue: str
    organisation: str
    raw_date: date
    date: str
    group_start_time: time
    group_end_time: time
    slots_starting_times: str
    bookings_url: Optional[str]


def async_timer(func):
    """Calculates the execution time of the Async function on top of which the decorator is assigned"""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        tic = timer()
        result = await func(*args, **kwargs)
        tac = timer()
        logging.debug(f"Function {func.__name__!r} executed in {(tac - tic):.4f}s")
        return result

    return wrapper


@timeit
def find_consecutive_slots(
        consecutive_count: int = 3,
        starting_time: time = time(18, 00),
        ending_time: time = time(22, 00),
        starting_date: date = datetime.now().date(),
        ending_date: date = datetime.now().date() + timedelta(days=3)
) -> List[List[SportScanner]]:
    """Finds consecutively overlapping slots i.e. end time of one slot overlaps with start time of
    another and calculates the `n` consecutive slots
    Returns: List of grouped consecutively occurring slots
    """

    slots = get_all_rows(
        engine, SportScanner,
        select(SportScanner).where(SportScanner.spaces > 0)
        .where(SportScanner.starting_time >= starting_time)
        .where(SportScanner.ending_time <= ending_time)
        .where(SportScanner.date >= starting_date)
        .where(SportScanner.date <= ending_date)
    )
    sports_centre_lists = get_all_rows(engine, SportsVenue, select(SportsVenue))
    dates: List[date] = list(set([row.date for row in slots]))
    consecutive_slots_list = []
    parameter_sets = [(x, y) for x, y in itertools.product(dates, sports_centre_lists)]

    for target_date, venue in parameter_sets:
        venue = venue.slug
        logging.debug(
            f"Extracting consecutive slots for venue slug: {venue} / date: {target_date}"
        )
        while True:
            consecutive_slots = []
            filtered_slots = [
                slot
                for slot in slots
                if slot.venue_slug == venue and slot.date == target_date
            ]
            sorted_slots = sorted(
                filtered_slots, key=lambda slot: slot.starting_time
            )
            logging.debug(sorted_slots)

            for i in range(len(sorted_slots) - 1):
                slot1 = sorted_slots[i]
                slot2 = sorted_slots[i + 1]

                if slot1.ending_time >= slot2.starting_time:
                    consecutive_slots.append(slot1)

                    if len(consecutive_slots) == consecutive_count - 1:
                        consecutive_slots.append(slot2)
                        break
                else:
                    consecutive_slots = []

            if len(consecutive_slots) == consecutive_count:
                consecutive_slots_list.append(consecutive_slots)
                # Remove the found slots from the data
                slots.remove(consecutive_slots[0])

            else:
                break  # No more consecutive slots found

    logging.debug(f"Top 3 Consecutive slots calculations:\n{consecutive_slots_list[:3]}")
    return consecutive_slots_list


@timeit
def format_consecutive_slots_groupings(
        consecutive_slots: List[List[SportScanner]]
) -> List[ConsecutiveSlotsCarousalDisplay]:
    temp = []
    for group_for_consecutive_slots in consecutive_slots:
        gather_slots_starting_times = []
        for slot in group_for_consecutive_slots:
            gather_slots_starting_times.append(
                slot.starting_time.strftime("%H:%M")
            )
        display_message_slots_starting_times: str = ("Slots starting at "
                                                     f"{', '.join(gather_slots_starting_times)}")

        logging.debug("Getting sports venue data from tables for slug replace with names")
        sports_venues: List[SportsVenue] = get_all_rows(engine, SportsVenue, select(SportsVenue))
        venue_slug_map = {venue.slug: venue for venue in sports_venues}

        initial_slot_in_group: SportScanner = group_for_consecutive_slots[0]
        final_slot_in_group: SportScanner = group_for_consecutive_slots[0]
        # replacing slug with names
        if initial_slot_in_group.venue_slug in venue_slug_map:
            # Replace venue_slug with the corresponding slug from SportsVenue
            venue_name_lookup = venue_slug_map[initial_slot_in_group.venue_slug].venue_name

            temp.append(
                ConsecutiveSlotsCarousalDisplay(
                    distance="Approx x. miles away",
                    venue=venue_name_lookup,
                    organisation=initial_slot_in_group.organisation,
                    raw_date=initial_slot_in_group.date,
                    date=initial_slot_in_group.date.strftime("%Y-%m-%d (%A)"),
                    group_start_time=initial_slot_in_group.starting_time,
                    group_end_time=final_slot_in_group.starting_time,
                    slots_starting_times=display_message_slots_starting_times,
                    bookings_url=initial_slot_in_group.booking_url
                )
            )
    sorted_groupings_for_consecutive_slots = sorted(
        temp, key=lambda x: (x.distance, x.raw_date, x.group_start_time)
    )
    logging.debug(f"Top formatted consecutive slot grouping for Carousal:\n{sorted_groupings_for_consecutive_slots[:1]}")
    return sorted_groupings_for_consecutive_slots


if __name__ == "__main__":
    """Write a test here for calculating consecutive slots"""
    logging.info("This scripts cannot be called standalone for now")
