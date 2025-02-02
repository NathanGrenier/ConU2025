import logging
import os
import re
from enum import Enum
from typing import Dict, List

import influxdb_client
import pandas as pd
from influxdb_client.client.write_api import SYNCHRONOUS

from config import (
    AIR_QUALITY_FILE_PATH,
    CLEANED_AIR_QUALITY_FILE_PATH,
    CLEANED_STATIONS_FILE_PATH,
    CLEANED_VIOLATIONS_FILE_PATH,
    DUMP_PATH,
    INFLUXDB_BUCKET,
    STATIONS_FILE_PATH,
    VIOLATIONS_FILE_PATH,
    influxdbClient,
    logger,
)


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


def createBucket(bucketName: str) -> None:
    logger.debug(f"Checking if bucket '{bucketName}' exists...")
    bucketsApi = influxdbClient.buckets_api()
    try:
        existingBuckets = bucketsApi.find_buckets().buckets
        if not any(b.name == bucketName for b in existingBuckets):
            logger.info(f"Creating bucket '{bucketName}'")
            bucketsApi.create_bucket(
                bucket_name=bucketName,
                org=influxdbClient.org,
            )
        else:
            logger.debug(f"Bucket '{bucketName}' already exists")
    except Exception as e:
        logger.error(f"Error creating bucket '{bucketName}': {str(e)}")


def uploadDfToInfluxDb(
    path: str, annotations: Dict[str, str], cleanUpload: bool = True
) -> None:
    bucket = annotations["bucket"]
    # createBucket(bucket)

    if cleanUpload:
        logger.info(
            f"Deleting all '{annotations['data_frame_measurement_name']}' records from bucket '{bucket}'"
        )
        delete_api = influxdbClient.delete_api()
        start = "1970-01-01T00:00:00Z"
        stop = "2100-01-01T00:00:00Z"
        delete_api.delete(
            start,
            stop,
            f'_measurement="{annotations["data_frame_measurement_name"]}"',
            bucket=bucket,
        )

    logger.info(f"Uploading {path} to InfluxDB...")
    for chunk in pd.read_csv(path, chunksize=100_000):
        with influxdbClient.write_api(write_options=SYNCHRONOUS) as write_api:
            try:
                write_api.write(record=chunk, **annotations)
                logger.debug(f"Uploaded {len(chunk)} records to InfluxDB")
            except influxdb_client.client.exceptions.InfluxDBError as e:
                logger.error(e)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    UPLOAD = True

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

    # if UPLOAD:
    #     uploadDfToInfluxDb(
    #         CLEANED_AIR_QUALITY_FILE_PATH,
    #         {
    #             "bucket": f"{INFLUXDB_BUCKET}",
    #             "data_frame_measurement_name": "air_quality",
    #             "data_frame_tag_columns": ["stationId", "pollutant"],
    #             "data_frame_timestamp_column": "timestamp",
    #         },
    #         cleanUpload=True,
    #     )
    # else:
    #     logger.info(f"Skipping InfluxDB Upload of: {CLEANED_AIR_QUALITY_FILE_PATH}")

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

        dumpData(df_violations, f"{CLEANED_VIOLATIONS_FILE_PATH}")

    # if UPLOAD:
    #     uploadDfToInfluxDb(
    #         f"{CLEANED_VIOLATIONS_FILE_PATH}",
    #         {
    #             "bucket": INFLUXDB_BUCKET,
    #             "data_frame_measurement_name": "violations",
    #             "data_frame_tag_columns": ["location"],
    #             "data_frame_field_columns": [
    #                 "offender_name",
    #                 "offence",
    #                 "location",
    #                 "judgment_date",
    #                 "amount_claimed",
    #                 "sentence",
    #                 "regulation_violated",
    #                 "domain",
    #             ],
    #             "data_frame_timestamp_column": "infraction_date",
    #         },
    #         cleanUpload=True,
    #     )
    # else:
    #     logger.info(f"Skipping InfluxDB Upload of: {CLEANED_VIOLATIONS_FILE_PATH}")

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

        # # Add a constant timestamp (e.g., Unix epoch 0)
        # df_stations["timestamp"] = "1970-01-01T00:00:00Z"

        dumpData(df_stations, f"{CLEANED_STATIONS_FILE_PATH}")

    # if UPLOAD:
    #     uploadDfToInfluxDb(
    #         f"{CLEANED_STATIONS_FILE_PATH}",
    #         {
    #             "bucket": INFLUXDB_BUCKET,
    #             "data_frame_measurement_name": "stations",
    #             "data_frame_tag_columns": ["station_id"],  # Tag for efficient joins
    #             "data_frame_field_columns": [
    #                 "name",
    #                 "address",
    #                 "latitude",
    #                 "longitude",
    #                 "status",
    #             ],
    #             "data_frame_timestamp_column": "timestamp",
    #         },
    #         cleanUpload=True,
    #     )
    # else:
    #     logger.info(f"Skipping InfluxDB Upload of: {CLEANED_STATIONS_FILE_PATH}")
