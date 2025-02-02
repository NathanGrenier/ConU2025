import logging
import os
import re
from enum import Enum
from typing import Dict, List

import influxdb_client
import numpy as np
import pandas as pd
import psycopg
from influxdb_client.client.write_api import SYNCHRONOUS
from psycopg import sql
from psycopg.errors import UniqueViolation

from config import (
    CLEANED_STATIONS_FILE_PATH,
    POSTGRES_CONFIG,
    logger,
)


def insert_stations(cursor, df_stations):
    df_stations = df_stations.replace({np.nan: None})

    insert_query = sql.SQL("""
        INSERT INTO stations (
            station_id, gov_reference_number, status, name, address, city, 
            latitude, longitude, x_coord, y_coord, sector_id, sector_name, 
            height, timestamp
        ) VALUES (
            %(station_id)s, %(gov_reference_number)s, %(status)s, %(name)s,
            %(address)s, %(city)s, %(latitude)s, %(longitude)s, %(x_coord)s,
            %(y_coord)s, %(sector_id)s, %(sector_name)s, %(height)s, %(timestamp)s
        ) ON CONFLICT (station_id) DO NOTHING;
    """)

    try:
        # Convert DataFrame to list of dictionaries
        records = df_stations.to_dict("records")

        # Use execute_batch for bulk insertion
        psycopg.extras.execute_batch(
            cursor,
            insert_query,
            records,
            page_size=100,  # Adjust based on your needs
        )

        logger.info(f"Inserted/updated {len(df_stations)} stations successfully")

    except UniqueViolation as e:
        logger.error(f"Duplicate station_id found: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inserting stations: {e}")
        raise


if __name__ == "__main__":
    try:
        with psycopg.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cursor:
                df_stations = pd.read_csv(CLEANED_STATIONS_FILE_PATH)

                expected_columns = [
                    "station_id",
                    "gov_reference_number",
                    "status",
                    "name",
                    "address",
                    "city",
                    "latitude",
                    "longitude",
                    "x_coord",
                    "y_coord",
                    "sector_id",
                    "sector_name",
                    "height",
                    "timestamp",
                ]

                if list(df_stations.columns) != expected_columns:
                    df_stations = df_stations[expected_columns]

                insert_stations(cursor, df_stations)

            conn.commit()

    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
