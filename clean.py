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
    DUMP_PATH,
    INFLUXDB_BUCKET,
    VIOLATIONS_FILE_PATH,
    influxdbClient,
    logger,
)


class ViolationDomain(Enum):
    AIR = "AIR"
    WATER = "EAU"


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


def combineDateHour(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["hour"].astype(str) + ":00:00", format="%Y-%m-%d %H:%M:%S"
    )
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


def uploadDfToInfluxDb(
    path: str, annotations: Dict[str, str], cleanUpload: bool = True
) -> None:
    # airQualityAnnotations = [
    #     "#group,true,true,true,false,false",
    #     "#datatype,measurement,tag,tag,long,dateTime:RFC3339",
    #     "#default,air_quality,,,,",
    # ]

    if cleanUpload:
        logger.info(f"Deleting all records from InfluxDB bucket {INFLUXDB_BUCKET}")
        delete_api = influxdbClient.delete_api()
        start = "1970-01-01T00:00:00Z"
        stop = "2100-01-01T00:00:00Z"
        delete_api.delete(
            start, stop, '_measurement="air_quality"', bucket=INFLUXDB_BUCKET
        )

    for chunk in pd.read_csv(path, chunksize=100_000):
        with influxdbClient.write_api(write_options=SYNCHRONOUS) as write_api:
            try:
                write_api.write(record=chunk, **annotations)
                logger.debug(f"Uploaded {len(chunk)} records to InfluxDB")
            except influxdb_client.client.exceptions.InfluxDBError as e:
                logger.error(e)


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    if not os.path.exists(CLEANED_AIR_QUALITY_FILE_PATH):
        logger.info("Cleaned Air Quality Data not Found: Cleaning Air Quality Data")
        df_air_quality = pd.read_csv(f"{AIR_QUALITY_FILE_PATH}")
        airQualityNameMapping = {
            "stationId": "stationId",
            "polluant": "pollutant",
            "valeur": "aqi",
            "date": "date",
            "heure": "hour",
        }
        df_air_quality = renameColumns(df_air_quality, airQualityNameMapping)

        df_air_quality = combineDateHour(df_air_quality)
        df_air_quality = df_air_quality.drop(columns=["date", "hour"])
        dumpData(df_air_quality, f"{DUMP_PATH}/cleaned_air_quality.csv")

    uploadDfToInfluxDb(
        CLEANED_AIR_QUALITY_FILE_PATH,
        {
            "bucket": f"{INFLUXDB_BUCKET}",
            "data_frame_measurement_name": "air_quality",
            "data_frame_tag_columns": ["stationId", "pollutant"],
            "data_frame_timestamp_column": "timestamp",
        },
        cleanUpload=True,
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
