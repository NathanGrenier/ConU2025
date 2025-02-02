import logging
import os
from typing import Dict, List

import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import sql
import psycopg2.extras

from config import (
    CLEANED_AIR_QUALITY_FILE_PATH,
    CLEANED_STATIONS_FILE_PATH,
    CLEANED_VIOLATIONS_FILE_PATH,
    POSTGRES_CONFIG,
    logger,
)

def insert_air_quality(cursor, df_air_quality):
    """Insert air quality measurements into PostgreSQL."""
    df_air_quality = df_air_quality.replace({np.nan: None})

    insert_query = sql.SQL("""
        INSERT INTO air_quality_measurements (
            station_id, pollutant, aqi, timestamp
        ) VALUES (
            %(station_id)s, %(pollutant)s, %(aqi)s, %(timestamp)s
        ) ON CONFLICT (station_id, pollutant, timestamp) DO NOTHING;
    """)

    try:
        records = df_air_quality.to_dict("records")
        psycopg2.extras.execute_batch(
            cursor,
            insert_query,
            records,
            page_size=1000,
        )
        logger.info(f"Inserted {len(df_air_quality)} air quality measurements successfully")
    except Exception as e:
        logger.error(f"Error inserting air quality measurements: {e}")
        raise


def insert_stations(cursor, df_stations):
    """Insert stations into PostgreSQL."""
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
        records = df_stations.to_dict("records")
        psycopg2.extras.execute_batch(
            cursor,
            insert_query,
            records,
            page_size=100,
        )
        logger.info(f"Inserted {len(df_stations)} stations successfully")
    except Exception as e:
        logger.error(f"Error inserting stations: {e}")
        raise


def insert_violations(cursor, df_violations):
    """Insert violations into PostgreSQL."""
    df_violations = df_violations.replace({np.nan: None})

    insert_query = sql.SQL("""
        INSERT INTO violations (
            offender_name, offence, location, latitude, longitude,
            infraction_date, judgment_date, amount_claimed, sentence,
            regulation_violated, domain
        ) VALUES (
            %(offender_name)s, %(offence)s, %(location)s, %(latitude)s,
            %(longitude)s, %(infraction_date)s, %(judgment_date)s,
            %(amount_claimed)s, %(sentence)s, %(regulation_violated)s,
            %(domain)s
        );
    """)

    try:
        records = df_violations.to_dict("records")
        psycopg2.extras.execute_batch(
            cursor,
            insert_query,
            records,
            page_size=1000,
        )
        logger.info(f"Inserted {len(df_violations)} violations successfully")
    except Exception as e:
        logger.error(f"Error inserting violations: {e}")
        raise


def upload_to_postgres(clean_upload: bool = True) -> None:
    """Upload all cleaned data to PostgreSQL."""
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cursor:
                if clean_upload:
                    logger.info("Cleaning up existing data...")
                    cursor.execute("TRUNCATE TABLE air_quality_measurements CASCADE;")
                    cursor.execute("TRUNCATE TABLE stations CASCADE;")
                    cursor.execute("TRUNCATE TABLE violations CASCADE;")
                
                # Upload stations first since they're referenced by air quality measurements
                if os.path.exists(CLEANED_STATIONS_FILE_PATH):
                    logger.info("Uploading stations data...")
                    df_stations = pd.read_csv(CLEANED_STATIONS_FILE_PATH)
                    df_stations["timestamp"] = "1970-01-01T00:00:00Z"  # Add constant timestamp
                    insert_stations(cursor, df_stations)

                # Upload air quality measurements
                if os.path.exists(CLEANED_AIR_QUALITY_FILE_PATH):
                    logger.info("Uploading air quality measurements...")
                    df_air_quality = pd.read_csv(CLEANED_AIR_QUALITY_FILE_PATH)
                    insert_air_quality(cursor, df_air_quality)

                # Upload violations
                if os.path.exists(CLEANED_VIOLATIONS_FILE_PATH):
                    logger.info("Uploading violations data...")
                    df_violations = pd.read_csv(CLEANED_VIOLATIONS_FILE_PATH)
                    insert_violations(cursor, df_violations)

            conn.commit()
            logger.info("Successfully uploaded all data to PostgreSQL")

    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise


if __name__ == "__main__":
    upload_to_postgres()
