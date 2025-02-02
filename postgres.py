import logging
import os
from typing import Dict, List
import time
import urllib.parse
import requests
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import threading

import numpy as np
import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.errors import UniqueViolation
import psycopg2.extras

from config import (
    CLEANED_AIR_QUALITY_FILE_PATH,
    CLEANED_STATIONS_FILE_PATH,
    CLEANED_VIOLATIONS_FILE_PATH,
    POSTGRES_CONFIG,
    logger,
)

requests_per_second = 2
# Rate limiter for geocoder.ca
request_semaphore = threading.Semaphore(requests_per_second)
request_times = []
request_lock = threading.Lock()

def wait_for_rate_limit():
    """Ensure we don't exceed the rate limit"""
    with request_lock:
        current_time = time.time()
        # Remove timestamps older than 1 second
        while request_times and current_time - request_times[0] > 1:
            request_times.pop(0)
        # If we've made 2 requests in the last second, wait
        if len(request_times) >= requests_per_second:
            sleep_time = 1 - (current_time - request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time + 0.1) # Add 0.1 second buffer
        request_times.append(current_time)

def geocode_address(address: str) -> tuple[float, float]:
    """
    Geocode an address using geocoder.ca API.
    Returns (latitude, longitude) tuple or (None, None) if geocoding fails.
    """
    try:
        encoded_address = urllib.parse.quote(address)
        url = f"https://geocoder.ca/?locate={encoded_address}&json=1"
        
        # Apply rate limiting
        wait_for_rate_limit()
        
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # geocoder.ca returns latt and longt
            if 'latt' in data and 'longt' in data:
                return float(data['latt']), float(data['longt'])
            elif 'error' in data:
                logger.warning(f"Geocoding error for address {address}: {data['error'].get('message', 'Unknown error')}")
                return None, None
        
        logger.warning(f"Geocoding failed for address {address}: {response.text}")
        return None, None
    except Exception as e:
        logger.warning(f"Geocoding failed for address {address}: {str(e)}")
        return None, None


def geocode_addresses_parallel(addresses: List[str], max_workers: int = 4) -> List[Dict[str, float]]:
    """
    Geocode multiple addresses in parallel using a thread pool.
    Returns a list of dictionaries containing latitude and longitude.
    Rate limited to respect geocoder.ca's limits.
    """
    coordinates = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all geocoding tasks
        future_to_address = {
            executor.submit(geocode_address, address): address 
            for address in addresses
        }
        
        total = len(addresses)
        completed = 0
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_address):
            address = future_to_address[future]
            try:
                lat, lon = future.result()
                coordinates.append({'latitude': lat, 'longitude': lon})
                completed += 1
                if lat and lon:
                    logger.info(f"Successfully geocoded ({completed}/{total}): {address}")
                else:
                    logger.warning(f"Failed to geocode ({completed}/{total}): {address}")
            except Exception as e:
                logger.error(f"Error geocoding {address}: {str(e)}")
                coordinates.append({'latitude': None, 'longitude': None})
                completed += 1
    
    return coordinates


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
    
    # Clean amount fields by removing currency symbols and all types of spaces
    for col in ['amount_claimed', 'sentence']:
        df_violations[col] = df_violations[col].apply(
            lambda x: float(''.join(c for c in str(x) if c.isdigit() or c == '.')) if x is not None else None
        )
    
    # Geocode addresses in parallel
    logger.info("Geocoding violation locations in parallel...")
    coordinates = geocode_addresses_parallel(df_violations['location'].tolist())
    
    coord_df = pd.DataFrame(coordinates)
    df_violations['latitude'] = coord_df['latitude']
    df_violations['longitude'] = coord_df['longitude']

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
    upload_to_postgres(clean_upload=True)
