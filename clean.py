import logging
import os
import re
import time
import urllib.parse
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import requests

from config import (
    AIR_QUALITY_FILE_PATH,
    CLEANED_AIR_QUALITY_FILE_PATH,
    CLEANED_STATIONS_FILE_PATH,
    CLEANED_VIOLATIONS_FILE_PATH,
    STATIONS_FILE_PATH,
    VIOLATIONS_FILE_PATH,
    logger,
)

# Rate limiter settings for geocoder.ca
requests_per_second = 2
request_semaphore = threading.Semaphore(requests_per_second)
request_times = []
request_lock = threading.Lock()


class ViolationDomain(Enum):
    AIR = "AIR"
    WATER = "EAU"


class StationStatus(Enum):
    OPEN = "ouvert"
    CLOSED = "fermé"


def renameColumns(df: pd.DataFrame, columnMapping) -> pd.DataFrame:
    return df.rename(columns=columnMapping)


def keepColumns(df: pd.DataFrame, keepColumns: List[str]) -> pd.DataFrame:
    return df_violations[keepColumns]


def dumpData(df: pd.DataFrame, filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(f"{filename}", index=False)


def cleanViolations(df: pd.DataFrame) -> pd.DataFrame:
    # Clean the regulation_violated column to only keep the violation code
    regex = r"\d+-\d+"
    df["regulation_violated"] = df["regulation_violated"].apply(
        lambda x: re.search(regex, x).group() if re.search(regex, x) else x
    )

    return df


def cleanStations(df: pd.DataFrame) -> pd.DataFrame:
    statusMapping = {"ouvert": "open", "fermé": "closed"}
    df["status"] = df["status"].map(statusMapping).fillna(df["status"])

    return df


def combineDateHour(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["hour"].astype(str) + ":00:00", format="%Y-%m-%d %H:%M:%S"
    )
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


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
                time.sleep(sleep_time + 0.25)  # Add small buffer
        request_times.append(current_time)


def geocode_address(address: str) -> Tuple[float, float]:
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


def clean_amount_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Clean amount fields by removing currency symbols and converting to floats"""
    def clean_amount(x):
        if pd.isna(x) or str(x).strip() == '':
            return None
        try:
            digits = ''.join(c for c in str(x) if c.isdigit() or c == '.')
            return float(digits) if digits else None
        except (ValueError, TypeError):
            return None
            
    for col in ['amount_claimed', 'sentence']:
        df[col] = df[col].apply(clean_amount)
    return df


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    ### Air Quality ###
    if not os.path.exists(CLEANED_AIR_QUALITY_FILE_PATH):
        logger.info(
            f"Cleaned Air Quality Data not Found: Cleaning Air Quality Data ({CLEANED_AIR_QUALITY_FILE_PATH})"
        )
        df_air_quality = pd.read_csv(f"{AIR_QUALITY_FILE_PATH}")
        airQualityNameMapping = {
            "stationId": "station_id",
            "polluant": "pollutant",
            "valeur": "aqi",
            "date": "date",
            "heure": "hour",
        }
        df_air_quality = renameColumns(df_air_quality, airQualityNameMapping)

        df_air_quality = combineDateHour(df_air_quality)
        df_air_quality = df_air_quality.drop(columns=["date", "hour"])
        dumpData(df_air_quality, f"{CLEANED_AIR_QUALITY_FILE_PATH}")

    ### Violations ###
    if not os.path.exists(CLEANED_VIOLATIONS_FILE_PATH):
        logger.info(
            f"Cleaned Violations Data not Found: Cleaning Violations Data ({CLEANED_VIOLATIONS_FILE_PATH})"
        )
        df_violations = pd.read_csv(f"{VIOLATIONS_FILE_PATH}")
        violationsNameMapping = {
            "nom_contrevenant": "offender_name",
            "infraction": "offence",
            "lieu_infraction": "location",
            "date_infraction": "infraction_date",
            "date_jugement": "judgment_date",
            "montant_reclame": "amount_claimed",
            "sentence": "sentence",
            "reglement": "regulation_violated",
            "domaine": "domain",
        }
        df_violations = renameColumns(df_violations, violationsNameMapping)

        df_violations = cleanViolations(df_violations)
        
        # Clean amount fields
        df_violations = clean_amount_fields(df_violations)
        
        # Geocode violation locations
        logger.info("Geocoding violation locations in parallel...")
        coordinates = geocode_addresses_parallel(df_violations['location'].tolist())
        coord_df = pd.DataFrame(coordinates)
        df_violations['latitude'] = coord_df['latitude']
        df_violations['longitude'] = coord_df['longitude']

        dumpData(df_violations, f"{CLEANED_VIOLATIONS_FILE_PATH}")

    ### Station ###
    if not os.path.exists(f"{CLEANED_STATIONS_FILE_PATH}"):
        logger.info(
            f"Cleaned Stations Data not Found: Cleaning Stations Data ({CLEANED_STATIONS_FILE_PATH})"
        )
        df_stations = pd.read_csv(f"{STATIONS_FILE_PATH}")

        stationNameMapping = {
            "numero_station": "station_id",
            "SNPA": "gov_reference_number",
            "statut": "status",
            "nom": "name",
            "adresse": "address",
            "arrondissement_ville": "city",
            "latitude": "latitude",  # geographic reference WGS84
            "longitude": "longitude",  # geographic reference WGS84
            "X": "x_coord",  # MTM8 projection
            "Y": "y_coord",  # MTM8 projection
            "secteur_id": "sector_id",
            "secteur_nom": "sector_name",
            "hauteur": "height",  # In Meters
        }
        df_stations = renameColumns(df_stations, stationNameMapping)
        df_stations = cleanStations(df_stations)

        dumpData(df_stations, f"{CLEANED_STATIONS_FILE_PATH}")
